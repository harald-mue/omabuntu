// SPDX-License-Identifier: MIT
// Closed owned BlueZ agent/action bridge. No default agent, trust or policy writes.
#include <QtCore>
#include <QtDBus>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>
#include <cstdio>

static const QString agentPath = "/org/omabuntu/BluetoothAgent";
static bool matches(const QString &s, const char *pattern) {
    return QRegularExpression(QString::fromLatin1(pattern)).match(s).hasMatch();
}
static QDBusMessage message(const QString &owner, const QString &path,
                            const QString &iface, const QString &method, const QVariantList &args = {}) {
    auto m = QDBusMessage::createMethodCall(owner, path, iface, method);
    m.setAutoStartService(false); m.setArguments(args); return m;
}
static QString errorName(const QDBusMessage &m) {
    const QString name = m.errorName();
    static const QSet<QString> allowed = {
        "org.bluez.Error.Failed", "org.bluez.Error.NotReady", "org.bluez.Error.InProgress",
        "org.bluez.Error.AlreadyConnected", "org.bluez.Error.NotConnected", "org.bluez.Error.DoesNotExist",
        "org.bluez.Error.AlreadyExists", "org.bluez.Error.InvalidArguments", "org.bluez.Error.Rejected",
        "org.bluez.Error.Canceled", "org.bluez.Error.AuthenticationCanceled", "org.bluez.Error.AuthenticationFailed",
        "org.bluez.Error.AuthenticationRejected", "org.bluez.Error.AuthenticationTimeout",
        "org.bluez.Error.ConnectionAttemptFailed", "org.bluez.Error.NotAuthorized",
        "org.bluez.Error.BREDR.ProfileUnavailable", "org.freedesktop.DBus.Error.AccessDenied",
        "org.freedesktop.DBus.Error.NoReply", "org.freedesktop.DBus.Error.UnknownObject",
        "org.freedesktop.DBus.Error.UnknownInterface", "org.freedesktop.DBus.Error.ServiceUnknown"
    };
    return allowed.contains(name) ? name : "bluetooth-method-error";
}

class Bridge final : public QDBusVirtualObject {
    QDBusConnection bus;
    QString scope, owner, token, path, adapter, address, phase, promptId, promptKind;
    QDBusMessage held;
    bool registered = false, cancelled = false;
    QString displayedCode;
    uint displayedEntered = 0;
    int operationMs = 120000, promptMs = 90000;
    quint64 generation = 0, promptSequence = 0;
    QByteArray input;
    QSet<QString> usedTokens;
    QTimer deadline, promptDeadline;
    QElapsedTimer rateClock;
    int frames = 0;

    void emitEvent(QJsonObject event) {
        event.insert("scope", scope);
        const QByteArray bytes = QJsonDocument(event).toJson(QJsonDocument::Compact) + '\n';
        if (bytes.size() > 4096 || fwrite(bytes.constData(), 1, size_t(bytes.size()), stdout) != size_t(bytes.size())) {
            QCoreApplication::quit(); return;
        }
        fflush(stdout);
    }
    QDBusMessage call(const QString &p, const QString &iface, const QString &method, const QVariantList &args = {}) {
        return bus.call(message(owner, p, iface, method, args), QDBus::Block, 1500);
    }
    bool sameOwner() {
        if (!bus.isConnected() || owner.isEmpty()) return false;
        QDBusReply<QString> current = bus.interface()->serviceOwner("org.bluez");
        return current.isValid() && current.value() == owner;
    }
    bool properties(QVariantMap &p) {
        if (!sameOwner()) return false;
        auto reply = call(path, "org.freedesktop.DBus.Properties", "GetAll", {"org.bluez.Device1"});
        if (reply.type() == QDBusMessage::ErrorMessage || reply.arguments().size() != 1) return false;
        p = qdbus_cast<QVariantMap>(reply.arguments().first());
        return p.value("Address").toString() == address
            && qvariant_cast<QDBusObjectPath>(p.value("Adapter")).path() == adapter
            && p.value("Connected").metaType().id() == QMetaType::Bool
            && p.value("Paired").metaType().id() == QMetaType::Bool
            && p.value("Bonded").metaType().id() == QMetaType::Bool
            && p.value("Blocked").metaType().id() == QMetaType::Bool;
    }
    void clearPrompt(const QString &reason) {
        promptDeadline.stop();
        if (!promptId.isEmpty()) {
            if (held.type() == QDBusMessage::MethodCallMessage)
                bus.send(held.createErrorReply("org.bluez.Error.Canceled", "Local pairing request ended"));
            emitEvent({{"event", "prompt-cleared"}, {"token", token}, {"prompt_id", promptId}, {"reason", reason}});
        }
        held = QDBusMessage(); promptId.clear(); promptKind.clear(); displayedCode.clear(); displayedEntered = 0;
    }
    void result(const QString &status, const QString &error = {}) {
        if (token.isEmpty()) return;
        clearPrompt("operation-ended"); deadline.stop();
        emitEvent({{"event", "result"}, {"token", token}, {"status", status}, {"error", error}});
        token.clear(); phase.clear(); ++generation;
    }
    void cancelOwned(const QString &reason) {
        if (token.isEmpty() || cancelled) return;
        cancelled = true; clearPrompt("cancelled");
        // Only our originating Pair is cancellable. Other in-flight operations
        // become uncertain; there is no automatic disconnect or compensation.
        if (phase != "Pair" || !sameOwner()) { result("uncertain", reason); return; }
        const quint64 serial = generation;
        auto *watch = new QDBusPendingCallWatcher(bus.asyncCall(message(owner, path, "org.bluez.Device1", "CancelPairing"), 3000), this);
        QObject::connect(watch, &QDBusPendingCallWatcher::finished, this, [this, watch, serial, reason] {
            auto reply = watch->reply(); watch->deleteLater();
            if (serial != generation || token.isEmpty()) return;
            result(reply.type() == QDBusMessage::ErrorMessage ? "uncertain" : "cancelled",
                   reply.type() == QDBusMessage::ErrorMessage ? errorName(reply) : reason);
        });
    }
    void invoke(const QString &method) {
        phase = method;
        const quint64 serial = generation;
        const QString target = method == "RemoveDevice" ? adapter : path;
        const QString iface = method == "RemoveDevice" ? "org.bluez.Adapter1" : "org.bluez.Device1";
        QVariantList args;
        if (method == "RemoveDevice") args << QVariant::fromValue(QDBusObjectPath(path));
        auto *watch = new QDBusPendingCallWatcher(bus.asyncCall(message(owner, target, iface, method, args), 120000), this);
        QObject::connect(watch, &QDBusPendingCallWatcher::finished, this, [this, watch, serial, method] {
            auto reply = watch->reply(); watch->deleteLater();
            if (serial != generation || token.isEmpty() || cancelled) return;
            if (!sameOwner()) { result("uncertain", "bluetooth-owner-lost"); return; }
            if (reply.type() == QDBusMessage::ErrorMessage) {
                const QString error = errorName(reply);
                const bool uncertain = error == "org.freedesktop.DBus.Error.NoReply" || error == "bluetooth-method-error";
                result(uncertain ? "uncertain" : "error", error); return;
            }
            if (method == "RemoveDevice") {
                auto check = call(path, "org.freedesktop.DBus.Properties", "GetAll", {"org.bluez.Device1"});
                const bool removed = check.type() == QDBusMessage::ErrorMessage && check.errorName() == "org.freedesktop.DBus.Error.UnknownObject";
                result(removed ? "observed" : "uncertain", removed ? "" : "forget-readback"); return;
            }
            QVariantMap p;
            if (!properties(p)) { result("uncertain", "device-identity-or-readback-lost"); return; }
            if (method == "Pair") {
                clearPrompt("pair-finished");
                if (!p.value("Paired").toBool()) { result("uncertain", "pair-not-observed"); return; }
                // One followup only, from this exact successful pairing generation.
                invoke("Connect"); return;
            }
            const bool observed = p.value("Connected").toBool() == (method == "Connect");
            result(observed ? "observed" : "uncertain", observed ? "" : "connection-readback-mismatch");
        });
    }
    void command(const QJsonObject &packet) {
        const QString op = packet.value("op").toString();
        if (packet.value("scope").toString() != scope) return;
        QSet<QString> keys{"op", "scope"};
        if (op == "answer") keys.unite({"token", "prompt_id", "accept", "value"});
        else if (op == "cancel") keys.insert("token");
        else if (op == "connect" || op == "disconnect" || op == "forget") keys.unite({"token", "path", "adapter", "address", "paired", "connected"});
        else if (op != "stop") { QCoreApplication::quit(); return; }
        for (const auto &key : packet.keys()) if (!keys.contains(key)) { QCoreApplication::quit(); return; }
        if (op == "stop") { cancelOwned("session-ended"); QCoreApplication::quit(); return; }
        if (op == "cancel") {
            if (packet.value("token").toString() == token) cancelOwned("explicit-cancel");
            return;
        }
        if (op == "answer") {
            if (packet.value("token").toString() != token || packet.value("prompt_id").toString() != promptId
                || held.type() != QDBusMessage::MethodCallMessage || !sameOwner() || cancelled) return;
            QVariantMap proof;
            if (!properties(proof)) { result("uncertain", "device-identity-lost-at-answer"); return; }
            const bool accepted = packet.value("accept").isBool() && packet.value("accept").toBool();
            QVariantList args;
            const QString value = packet.value("value").toString();
            bool valid = true;
            if (promptKind == "RequestPinCode") {
                valid = matches(value, "^[A-Za-z0-9]{1,16}$"); args << value;
            } else if (promptKind == "RequestPasskey") {
                valid = matches(value, "^[0-9]{1,6}$"); args << QVariant::fromValue(quint32(value.toUInt()));
            }
            if (accepted && !valid) { emitEvent({{"event", "input-invalid"}, {"token", token}, {"prompt_id", promptId}}); return; }
            auto reply = accepted ? held.createReply(args) : held.createErrorReply("org.bluez.Error.Rejected", "Rejected locally");
            bus.send(reply); held = QDBusMessage(); clearPrompt(accepted ? "answered" : "rejected");
            return;
        }
        const QString requestToken = packet.value("token").toString();
        if (op != "connect" && op != "disconnect" && op != "forget") return;
        if (!token.isEmpty() || !registered || !sameOwner() || !matches(requestToken, "^[a-f0-9]{16,64}$")) return;
        const QString p = packet.value("path").toString(), a = packet.value("adapter").toString(), addr = packet.value("address").toString();
        if (!matches(a, "^/org/bluez/hci[0-9]{1,3}$") || !p.startsWith(a + "/dev_")
            || !matches(p, "^/org/bluez/hci[0-9]{1,3}/dev_[A-F0-9]{2}(_[A-F0-9]{2}){5}$")
            || !matches(addr, "^[A-F0-9]{2}(:[A-F0-9]{2}){5}$")) return;
        if (usedTokens.contains(requestToken)) return;
        if (usedTokens.size() >= 4096) { emitEvent({{"event", "unavailable"}, {"error", "operation-history-limit"}}); QCoreApplication::quit(); return; }
        usedTokens.insert(requestToken);
        path = p; adapter = a; address = addr; token = requestToken; cancelled = false; ++generation;
        QVariantMap props;
        if (!properties(props) || !packet.value("paired").isBool() || !packet.value("connected").isBool()
            || props.value("Paired").toBool() != packet.value("paired").toBool()
            || props.value("Connected").toBool() != packet.value("connected").toBool()) {
            result("error", "device-state-or-identity-changed"); return;
        }
        if (op == "connect" && props.value("Blocked").toBool()) { result("error", "device-blocked"); return; }
        if (op == "connect") {
            auto power = call(adapter, "org.freedesktop.DBus.Properties", "Get", {"org.bluez.Adapter1", "Powered"});
            if (power.type() == QDBusMessage::ErrorMessage || power.arguments().size() != 1
                || qvariant_cast<QDBusVariant>(power.arguments().first()).variant().metaType().id() != QMetaType::Bool
                || !qvariant_cast<QDBusVariant>(power.arguments().first()).variant().toBool()) { result("error", "adapter-not-powered"); return; }
        }
        deadline.start(operationMs);
        invoke(op == "forget" ? "RemoveDevice" : op == "disconnect" ? "Disconnect" : (props.value("Paired").toBool() || props.value("Bonded").toBool()) ? "Connect" : "Pair");
    }
public:
    Bridge(const QDBusConnection &connection, QString s) : bus(connection), scope(std::move(s)) {
        deadline.setSingleShot(true); promptDeadline.setSingleShot(true); rateClock.start();
#ifdef OMABUNTU_BLUETOOTH_TEST_BUS
        bool ok = false;
        int value = qEnvironmentVariableIntValue("OMABUNTU_TEST_OPERATION_MS", &ok);
        if (ok && value >= 20 && value <= 120000) operationMs = value;
        value = qEnvironmentVariableIntValue("OMABUNTU_TEST_PROMPT_MS", &ok);
        if (ok && value >= 20 && value <= 90000) promptMs = value;
#endif
        QObject::connect(&deadline, &QTimer::timeout, this, [this] { cancelOwned("operation-timeout-uncertain"); });
        QObject::connect(&promptDeadline, &QTimer::timeout, this, [this] { cancelOwned("prompt-timeout"); });
    }
    ~Bridge() override {
        clearPrompt("session-ended");
        if (registered && sameOwner()) call("/org/bluez", "org.bluez.AgentManager1", "UnregisterAgent", {QVariant::fromValue(QDBusObjectPath(agentPath))});
        bus.unregisterObject(agentPath);
    }
    bool start() {
        QDBusReply<QString> proof = bus.interface()->serviceOwner("org.bluez");
        if (!proof.isValid()) return false;
        owner = proof.value(); QDBusReply<uint> uid = bus.interface()->serviceUid(owner);
#ifdef OMABUNTU_BLUETOOTH_TEST_BUS
        const uint expectedUid = getuid();
#else
        const uint expectedUid = 0;
#endif
        if (!uid.isValid() || uid.value() != expectedUid || !matches(owner, "^:[0-9]+\\.[0-9]+$")) return false;
        if (!bus.registerVirtualObject(agentPath, this, QDBusConnection::SingleNode)) return false;
        auto reply = call("/org/bluez", "org.bluez.AgentManager1", "RegisterAgent",
                          {QVariant::fromValue(QDBusObjectPath(agentPath)), "KeyboardDisplay"});
        if (reply.type() == QDBusMessage::ErrorMessage) return false;
        registered = true;
        auto *watcher = new QDBusServiceWatcher("org.bluez", bus, QDBusServiceWatcher::WatchForOwnerChange, this);
        QObject::connect(watcher, &QDBusServiceWatcher::serviceOwnerChanged, this, [this](const QString &, const QString &, const QString &next) {
            if (next != owner) { registered = false; result("uncertain", "bluetooth-owner-lost"); emitEvent({{"event", "unavailable"}, {"error", "bluetooth-owner-lost"}}); QCoreApplication::quit(); }
        });
        const int flags = fcntl(STDIN_FILENO, F_GETFL);
        if (flags < 0 || fcntl(STDIN_FILENO, F_SETFL, flags | O_NONBLOCK) < 0) return false;
        auto *notifier = new QSocketNotifier(STDIN_FILENO, QSocketNotifier::Read, this);
        QObject::connect(notifier, &QSocketNotifier::activated, this, [this] {
            char buffer[4096]; const ssize_t n = read(STDIN_FILENO, buffer, sizeof(buffer));
            if (n <= 0) { if (n == 0) QCoreApplication::quit(); return; }
            input.append(buffer, qsizetype(n));
            if (input.size() > 8192) { QCoreApplication::quit(); return; }
            int newline;
            while ((newline = input.indexOf('\n')) >= 0) {
                const QByteArray line = input.left(newline); input.remove(0, newline + 1);
                if (rateClock.elapsed() >= 60000) { rateClock.restart(); frames = 0; }
                if (line.size() > 4096 || ++frames > 128) { QCoreApplication::quit(); return; }
                QJsonParseError error; const auto doc = QJsonDocument::fromJson(line, &error);
                if (error.error != QJsonParseError::NoError || !doc.isObject()) { QCoreApplication::quit(); return; }
                command(doc.object());
            }
        });
        emitEvent({{"event", "ready"}}); return true;
    }
    QString introspect(const QString &) const override {
        return "<interface name=\"org.bluez.Agent1\">"
            "<method name=\"Release\"/><method name=\"Cancel\"/>"
            "<method name=\"RequestPinCode\"><arg type=\"o\" direction=\"in\"/><arg type=\"s\" direction=\"out\"/></method>"
            "<method name=\"RequestPasskey\"><arg type=\"o\" direction=\"in\"/><arg type=\"u\" direction=\"out\"/></method>"
            "<method name=\"DisplayPinCode\"><arg type=\"o\" direction=\"in\"/><arg type=\"s\" direction=\"in\"/></method>"
            "<method name=\"DisplayPasskey\"><arg type=\"o\" direction=\"in\"/><arg type=\"u\" direction=\"in\"/><arg type=\"q\" direction=\"in\"/></method>"
            "<method name=\"RequestConfirmation\"><arg type=\"o\" direction=\"in\"/><arg type=\"u\" direction=\"in\"/></method>"
            "<method name=\"RequestAuthorization\"><arg type=\"o\" direction=\"in\"/></method>"
            "<method name=\"AuthorizeService\"><arg type=\"o\" direction=\"in\"/><arg type=\"s\" direction=\"in\"/></method>"
            "</interface>";
    }
    bool handleMessage(const QDBusMessage &m, const QDBusConnection &) override {
        if (m.type() != QDBusMessage::MethodCallMessage) return false;
        if (m.service() != owner || !sameOwner() || m.interface() != "org.bluez.Agent1" || m.path() != agentPath) {
            bus.send(m.createErrorReply(QDBusError::AccessDenied, "Unadmitted agent caller")); return true;
        }
        const QString kind = m.member(); const auto args = m.arguments();
        const QHash<QString, QString> signatures = {{"Release", ""}, {"Cancel", ""}, {"RequestPinCode", "o"},
            {"RequestPasskey", "o"}, {"DisplayPinCode", "os"}, {"DisplayPasskey", "ouq"},
            {"RequestConfirmation", "ou"}, {"RequestAuthorization", "o"}, {"AuthorizeService", "os"}};
        if (!signatures.contains(kind) || m.signature() != signatures.value(kind)) {
            bus.send(m.createErrorReply("org.bluez.Error.Rejected", "Unsupported signature")); return true;
        }
        if (kind == "Release" && args.isEmpty()) {
            registered = false; clearPrompt("released"); result("uncertain", "agent-released"); bus.send(m.createReply());
            emitEvent({{"event", "unavailable"}, {"error", "agent-released"}}); QCoreApplication::quit(); return true;
        }
        if (kind == "Cancel" && args.isEmpty()) { clearPrompt("daemon-cancelled"); bus.send(m.createReply()); return true; }
        if (token.isEmpty() || cancelled || args.isEmpty() || qvariant_cast<QDBusObjectPath>(args[0]).path() != path
            || (phase != "Pair" && phase != "Connect")) {
            bus.send(m.createErrorReply("org.bluez.Error.Rejected", "No matching locally initiated operation")); return true;
        }
        QVariantMap proof;
        if (!properties(proof)) { bus.send(m.createErrorReply("org.bluez.Error.Rejected", "Device identity lost")); return true; }
        const bool display = kind == "DisplayPinCode" || kind == "DisplayPasskey";
        if (!promptId.isEmpty() && !(kind == "DisplayPasskey" && held.type() != QDBusMessage::MethodCallMessage && promptKind == kind)) {
            bus.send(m.createErrorReply("org.bluez.Error.Rejected", "A prompt is already pending")); return true;
        }
        QJsonObject event{{"event", "prompt"}, {"token", token}, {"kind", kind}};
        bool valid = false;
        if ((kind == "RequestPinCode" || kind == "RequestPasskey" || kind == "RequestAuthorization") && args.size() == 1) valid = true;
        if ((kind == "RequestConfirmation" && args.size() == 2) || (kind == "DisplayPasskey" && args.size() == 3)) {
            const uint code = args[1].toUInt(); valid = code <= 999999;
            event.insert("code", QString::number(code).rightJustified(6, '0'));
            if (kind == "DisplayPasskey") {
                const uint entered = args[2].toUInt();
                valid = valid && entered <= 6 && (promptId.isEmpty() || (displayedCode == event.value("code").toString() && entered >= displayedEntered));
                event.insert("entered", int(entered));
            }
        }
        if (kind == "DisplayPinCode" && args.size() == 2) {
            const QString code = args[1].toString(); valid = matches(code, "^[0-9]{6}$"); event.insert("code", code);
        }
        if (kind == "AuthorizeService" && args.size() == 2) {
            const QString uuid = args[1].toString().toLower();
            // No PAN, file transfer, serial/network or arbitrary profile policy.
            valid = matches(uuid, "^0000(1108|110a|110b|110c|110e|110f|1112|111e|111f|1124|1812)-0000-1000-8000-00805f9b34fb$");
            event.insert("uuid", uuid);
        }
        if (!valid) { bus.send(m.createErrorReply("org.bluez.Error.Rejected", "Unsupported or malformed request")); return true; }
        if (promptId.isEmpty()) promptId = QString::number(++promptSequence, 16);
        promptKind = kind; event.insert("prompt_id", promptId);
        if (display) bus.send(m.createReply()); else held = m;
        displayedCode = event.value("code").toString(); displayedEntered = uint(event.value("entered").toInt());
        emitEvent(event); promptDeadline.start(promptMs); return true;
    }
};

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const auto args = app.arguments();
    if (args.size() == 2 && args[1] == "--contract") {
#ifdef OMABUNTU_BLUETOOTH_TEST_BUS
        puts("{\"schema_version\":1,\"scope\":\"omabuntu-owned-bluez-agent-v1\",\"test_bus\":true}");
#else
        puts("{\"schema_version\":1,\"scope\":\"omabuntu-owned-bluez-agent-v1\",\"test_bus\":false}");
#endif
        return 0;
    }
    if (args.size() == 2 && args[1] == "--help") {
        puts("Owned Bluetooth agent: explicit --allow-owned-agent --allow-system-bus-connection-risk --scope=HEX required. No default agent or trust policy."); return 0;
    }
    QString scope, address = "unix:path=/run/dbus/system_bus_socket";
    bool agentGrant = false, busGrant = false;
    for (const QString &arg : args.mid(1)) {
        if (arg == "--allow-owned-agent") agentGrant = true;
        else if (arg == "--allow-system-bus-connection-risk") busGrant = true;
        else if (arg.startsWith("--scope=")) scope = arg.mid(8);
#ifdef OMABUNTU_BLUETOOTH_TEST_BUS
        else if (arg.startsWith("--test-bus=")) address = arg.mid(11);
#endif
        else return 2;
    }
    if (!agentGrant || !busGrant || !matches(scope, "^[a-f0-9]{16,64}$")) return 2;
#ifndef OMABUNTU_BLUETOOTH_TEST_BUS
    // Prove the existing fixed bus peer before Qt connects; no environment-selected bus.
    int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    const timeval timeout{1, 0};
    if (fd >= 0) setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    sockaddr_un endpoint{}; endpoint.sun_family = AF_UNIX; strcpy(endpoint.sun_path, "/run/dbus/system_bus_socket");
    ucred peer{}; socklen_t size = sizeof(peer);
    const bool safe = fd >= 0 && ::connect(fd, reinterpret_cast<sockaddr *>(&endpoint), sizeof(endpoint)) == 0
        && getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &peer, &size) == 0 && peer.uid == 0;
    if (fd >= 0) close(fd);
    if (!safe) return 3;
#endif
    auto bus = QDBusConnection::connectToBus(address, "omabuntu-owned-bluetooth");
    if (!bus.isConnected()) return 3;
    Bridge bridge(bus, scope);
    if (!bridge.start()) return 4;
    return app.exec();
}
