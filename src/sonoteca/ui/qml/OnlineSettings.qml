import QtQuick
import QtQuick.Controls
import "."

Popup {
    id: root
    property string error: ""
    property alias useInternetItem: useInternet  // para las pruebas
    property alias contactItem: contactField

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 520
    padding: 24
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openDialog() {
        useInternet.checked = !online.offline
        contactField.reset(online.contact, false)
        error = ""
        open()
    }
    function save() {
        var contact = contactField.text.trim()
        if (useInternet.checked && contact.indexOf("@") < 0 && contact.indexOf("http") !== 0) {
            error = "Indica un correo (con @) o una dirección web (que empiece por http)."
            return
        }
        online.setContact(contact)
        online.setOffline(!useInternet.checked)
        close()
    }

    contentItem: Column {
        spacing: 14
        Text { text: "Internet"; color: Theme.text; font.pixelSize: 22; font.weight: Font.Bold }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 13
            text: "La aplicación funciona sin conexión. Si activas internet, solo se usa para traer portadas (Cover Art Archive), datos de álbumes y artistas (MusicBrainz) y el resumen de un artista (Wikipedia). Son servicios gratuitos y no necesitan clave."
        }
        AppCheck { id: useInternet; text: "Usar internet" }
        EditorField { id: contactField; width: parent.width; key: "contact"; label: "Correo o web de contacto" }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 11
            text: "Esos servicios piden que cada aplicación se identifique. Este dato se envía en cada consulta, junto con el nombre de la aplicación. Puedes usar un correo o la dirección de tu perfil en GitHub."
        }
        Text { width: parent.width; visible: root.error !== ""; text: root.error; color: Theme.danger; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton { label: "Guardar"; primary: true; onClicked: root.save() }
        }
    }
}
