// Synthetic persistent sender for private notification integration tests only.
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusMessage>
#include <QDBusReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSocketNotifier>
#include <QTimer>
#include <iostream>
#include <unistd.h>

class Sender final : public QObject {
    Q_OBJECT
public:
    QDBusConnection bus = QDBusConnection::sessionBus();
    QString owner;
    uint notice = 0;
    int callbacks = 0;
    QByteArray pending;

    static void report(QJsonObject value) {
        std::cout << QJsonDocument(value).toJson(QJsonDocument::Compact).toStdString() << std::endl;
    }

    bool start() {
        if (!bus.isConnected() || !bus.interface()) return false;
        QDBusReply<QString> reply = bus.interface()->serviceOwner("org.freedesktop.Notifications");
        if (!reply.isValid()) return false;
        owner = reply.value();
        const QString path = "/org/freedesktop/Notifications";
        const QString iface = "org.freedesktop.Notifications";
        if (!bus.connect(owner, path, iface, "ActionInvoked", this, SLOT(action(uint,QString,QDBusMessage)))
            || !bus.connect(owner, path, iface, "NotificationClosed", this, SLOT(closed(uint,uint,QDBusMessage)))) return false;
        report({{"event", "ready"}, {"unique", bus.baseService()},
                {"owner", owner}, {"pid", QCoreApplication::applicationPid()}});
        return true;
    }

    void input() {
        char bytes[128];
        const auto size = ::read(STDIN_FILENO, bytes, sizeof(bytes));
        if (size <= 0) { QCoreApplication::quit(); return; }
        pending.append(bytes, int(size));
        if (pending.size() > 256) { QCoreApplication::exit(2); return; }
        while (pending.contains('\n')) {
            const auto at = pending.indexOf('\n');
            const auto verb = pending.left(at); pending.remove(0, at + 1);
            if (verb == "quit") { QCoreApplication::quit(); return; }
            if (verb == "status") {
                report({{"event", "status"}, {"id", int(notice)}, {"callbacks", callbacks}}); continue;
            }
            if (verb != "notify" && verb != "replace") { QCoreApplication::exit(2); return; }
            if (verb == "replace" && notice == 0) { QCoreApplication::exit(2); return; }
            auto request = QDBusMessage::createMethodCall(owner, "/org/freedesktop/Notifications",
                                                        "org.freedesktop.Notifications", "Notify");
            request << QString("Fixture") << uint(verb == "replace" ? notice : 0) << QString()
                    << QString("Cross-process fixture") << QString("Synthetic notification body")
                    << QStringList({"default", "Open fixture"}) << QVariantMap() << int(30000);
            const auto reply = bus.call(request, QDBus::Block, 2000);
            if (reply.type() != QDBusMessage::ReplyMessage || reply.signature() != "u" || reply.arguments().size() != 1) {
                report({{"event", "failed"}}); QCoreApplication::exit(2); return;
            }
            notice = reply.arguments().first().toUInt();
            if (notice == 0) { QCoreApplication::exit(2); return; }
            report({{"event", "sent"}, {"id", int(notice)}, {"replacement", verb == "replace"}});
        }
    }

public slots:
    void action(uint id, const QString &identifier, const QDBusMessage &message) {
        if (message.service() != owner) { QCoreApplication::exit(2); return; }
        if (id != notice || notice == 0) {
            report({{"event", "ignored-action"}, {"id", int(id)}}); return;
        }
        if (identifier != "default") { QCoreApplication::exit(2); return; }
        ++callbacks;
        report({{"event", "action"}, {"id", int(id)}, {"action", identifier}, {"count", callbacks}});
    }
    void closed(uint id, uint reason, const QDBusMessage &message) {
        if (message.service() != owner) { QCoreApplication::exit(2); return; }
        report({{"event", id == notice ? "closed" : "ignored-close"}, {"id", int(id)}, {"reason", int(reason)}});
    }
};

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    if (qEnvironmentVariable("DBUS_SESSION_BUS_ADDRESS") != "unix:path=/home/probe/runtime/private-bus"
        || qEnvironmentVariable("PRIVATE_OUTPUT_COUNT") != "1") return 2;
    Sender sender;
    if (!sender.start()) return 2;
    QSocketNotifier input(STDIN_FILENO, QSocketNotifier::Read);
    QObject::connect(&input, &QSocketNotifier::activated, &sender, &Sender::input);
    QTimer::singleShot(30000, &app, [] { QCoreApplication::exit(98); });
    return app.exec();
}

#include "sender.moc"
