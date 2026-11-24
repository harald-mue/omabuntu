// SPDX-License-Identifier: MIT
// Isolated fake BlueZ only. Never packaged or connected to a host bus.
#include <QtCore>
#include <QtDBus>
#include <cstdio>

static const QString devicePath = "/org/bluez/hci0/dev_00_11_22_33_44_55";
class Fake final : public QDBusVirtualObject {
    QDBusConnection bus;
    QString agentOwner, agentPath, mode, address;
    QDBusMessage pairReply;
    bool paired = false, connected = false, present = true;
    int pairs = 0, connects = 0, cancels = 0, registers = 0, unregisters = 0, removals = 0;
    int agentSuccess = 0, agentError = 0, entered = 0, wrongCallerDenied = 0;
    void agentCall(const QString &kind, QVariantList args, bool complete = true) {
        auto m = QDBusMessage::createMethodCall(agentOwner, agentPath, "org.bluez.Agent1", kind);
        m.setArguments(args);m.setAutoStartService(false);
        auto *w = new QDBusPendingCallWatcher(bus.asyncCall(m, 10000), this);
        QObject::connect(w, &QDBusPendingCallWatcher::finished, this, [this, w, complete, kind] {
            auto reply = w->reply();w->deleteLater();
            const bool ok = reply.type() != QDBusMessage::ErrorMessage;
            if (ok) ++agentSuccess;else ++agentError;
            if (!complete) return;
            if (mode == "display-update" && kind == "DisplayPasskey" && ok && entered < 6) {
                entered = 6;
                agentCall("DisplayPasskey", {QVariant::fromValue(QDBusObjectPath(devicePath)), quint32(42), QVariant::fromValue(quint16(6))});return;
            }
            if (mode == "daemon-cancel" && kind == "DisplayPinCode") {
                agentCall("Cancel", {}, false);
                QTimer::singleShot(40,this,[this]{
                    if (pairReply.type() == QDBusMessage::MethodCallMessage) {
                        bus.send(pairReply.createErrorReply("org.bluez.Error.AuthenticationCanceled", "synthetic"));pairReply=QDBusMessage();
                    }
                });return;
            }
            if (pairReply.type() != QDBusMessage::MethodCallMessage) return;
            if (ok) { paired = true;bus.send(pairReply.createReply()); }
            else bus.send(pairReply.createErrorReply("org.bluez.Error.AuthenticationRejected", "synthetic"));
            pairReply=QDBusMessage();
        });
    }
public:
    Fake(QDBusConnection b, QString m, QString a):bus(b),mode(std::move(m)),address(std::move(a)){}
    QString introspect(const QString &) const override { return ""; }
    bool handleMessage(const QDBusMessage &m,const QDBusConnection &) override {
        const QString method=m.member(),iface=m.interface(),path=m.path();
        if (iface=="org.bluez.AgentManager1") {
            if (method=="RegisterAgent") {
                agentOwner=m.service();agentPath=qvariant_cast<QDBusObjectPath>(m.arguments()[0]).path();
                ++registers;bus.send(m.createReply());return true;
            }
            if (method=="UnregisterAgent") {++unregisters;bus.send(m.createReply());return true;}
            bus.send(m.createErrorReply(QDBusError::AccessDenied,"No default agent permitted"));return true;
        }
        if (iface=="org.freedesktop.DBus.Properties") {
            if (method=="Set") {bus.send(m.createErrorReply(QDBusError::AccessDenied,"No policy writes permitted"));return true;}
            if (path=="/org/bluez/hci0" && method=="Get") {bus.send(m.createReply({QVariant::fromValue(QDBusVariant(true))}));return true;}
            if (path!=devicePath || !present) {bus.send(m.createErrorReply(QDBusError::UnknownObject,"synthetic removed"));return true;}
            QVariantMap p{{"Address", "00:11:22:33:44:55"},{"Adapter",QVariant::fromValue(QDBusObjectPath("/org/bluez/hci0"))},
                {"Paired",paired},{"Bonded",paired},{"Connected",connected},{"Blocked",false},{"Trusted",false}};
            bus.send(m.createReply(QVariantList{p}));return true;
        }
        if (iface=="org.bluez.Device1" && path==devicePath) {
            if (method=="Pair") {
                if (m.service()!=agentOwner) { bus.send(m.createErrorReply(QDBusError::AccessDenied,"Pair must use the registered agent connection"));return true; }
                ++pairs;pairReply=m;
                if(mode=="timeout")return true;
                if(mode=="release") {QTimer::singleShot(0,this,[this]{agentCall("Release",{},false);});return true;}
                if(mode=="owner-loss") {QTimer::singleShot(30,this,[this]{bus.unregisterService("org.bluez");});return true;}
                if(mode=="failure") {bus.send(m.createErrorReply("org.bluez.Error.AuthenticationFailed","synthetic"));pairReply=QDBusMessage();return true;}
                if(mode=="wrong-caller") {
                    auto outsider=QDBusConnection::connectToBus(address,"outsider");
                    auto request=QDBusMessage::createMethodCall(agentOwner,agentPath,"org.bluez.Agent1","RequestPinCode");
                    request.setArguments({QVariant::fromValue(QDBusObjectPath(devicePath))});
                    auto *w=new QDBusPendingCallWatcher(outsider.asyncCall(request,3000),this);
                    QObject::connect(w,&QDBusPendingCallWatcher::finished,this,[this,w]{
                        if(w->reply().errorName()=="org.freedesktop.DBus.Error.AccessDenied")++wrongCallerDenied;
                        w->deleteLater();agentCall("RequestPinCode",{QVariant::fromValue(QDBusObjectPath(devicePath))});
                    });return true;
                }
                QString kind="RequestPinCode";QVariantList args{QVariant::fromValue(QDBusObjectPath(devicePath))};
                if(mode=="passkey")kind="RequestPasskey";
                if(mode=="confirm") {kind="RequestConfirmation";args<<quint32(42);}
                if(mode=="authorization")kind="RequestAuthorization";
                if(mode=="service"||mode=="unsupported-service") {kind="AuthorizeService";args<<(mode=="service"?"0000110b-0000-1000-8000-00805f9b34fb":"00001116-0000-1000-8000-00805f9b34fb");}
                if(mode=="display-pin"||mode=="daemon-cancel") {kind="DisplayPinCode";args<<"000042";}
                if(mode=="display-passkey"||mode=="display-update") {kind="DisplayPasskey";args<<quint32(42)<<QVariant::fromValue(quint16(2));}
                if(mode=="wrong-device")args[0]=QVariant::fromValue(QDBusObjectPath("/org/bluez/hci0/dev_00_11_22_33_44_66"));
                if(mode=="bad-signature") {kind="RequestConfirmation";args<<"42";}
                QTimer::singleShot(0,this,[this,kind,args]{agentCall(kind,args);});return true;
            }
            if (method=="CancelPairing") {
                ++cancels;
                if(pairReply.type()==QDBusMessage::MethodCallMessage)bus.send(pairReply.createErrorReply("org.bluez.Error.AuthenticationCanceled","synthetic"));
                pairReply=QDBusMessage();bus.send(m.createReply());return true;
            }
            if(method=="Connect") {++connects;connected=true;bus.send(m.createReply());return true;}
            if(method=="Disconnect") {connected=false;bus.send(m.createReply());return true;}
        }
        if (iface=="org.bluez.Adapter1"&&method=="RemoveDevice") {++removals;present=false;paired=false;connected=false;bus.send(m.createReply());return true;}
        if (iface=="org.omabuntu.Test"&&method=="Report") {
            QJsonObject report{{"pairs",pairs},{"connects",connects},{"cancels",cancels},{"registers",registers},
              {"unregisters",unregisters},{"removals",removals},{"wrong_caller_denied",wrongCallerDenied},{"agent_success",agentSuccess},{"agent_error",agentError},{"paired",paired},{"connected",connected}};
            bus.send(m.createReply(QVariantList{QString::fromUtf8(QJsonDocument(report).toJson(QJsonDocument::Compact))}));return true;
        }
        bus.send(m.createErrorReply(QDBusError::UnknownMethod,"synthetic unsupported"));return true;
    }
};
int main(int argc,char**argv) {
    QCoreApplication app(argc,argv);
    if(app.arguments().size()!=3)return 2;
    auto bus=QDBusConnection::connectToBus(app.arguments()[1],"fake-bluez");
    if(!bus.isConnected()||!bus.registerService("org.bluez"))return 3;
    Fake fake(bus,app.arguments()[2],app.arguments()[1]);
    if(!bus.registerVirtualObject("/",&fake,QDBusConnection::SubPath))return 4;
    puts("ready");fflush(stdout);return app.exec();
}
