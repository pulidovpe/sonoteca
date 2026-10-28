import QtQuick
import QtQuick.Controls
import "."

// Ajustes de la traducción de letras: idioma de destino y clave de DeepL (se guarda en el llavero del sistema)
Popup {
    id: root
    property string error: ""
    property alias langItem: langField      // para las pruebas
    property alias keyItem: keyField

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 520
    padding: 24
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openDialog() {
        langField.reset(lyrics.translateLang, false)
        keyField.reset("", false)
        error = ""
        open()
    }
    function save() {
        var problem = lyrics.setTranslateLang(langField.text)
        if (problem === "" && keyField.text.trim() !== "") problem = lyrics.setApiKey(keyField.text)
        if (problem !== "") { error = problem; return }
        close()
    }

    contentItem: Column {
        spacing: 14
        Text { text: "Traducción de letras"; color: Theme.text; font.pixelSize: 22; font.weight: Font.Bold }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 13
            text: "Las letras se traducen con DeepL usando tu propia clave. El plan gratuito (\u00abAPI Free\u00bb) incluye 500\u00a0000 caracteres al mes y se detiene al llegar al l\u00edmite; una letra suele usar entre 1\u00a0500 y 2\u00a0500. Cada traducci\u00f3n se guarda y no se vuelve a pedir. Solo se env\u00eda a DeepL el texto de la letra."
        }
        EditorField { id: langField; width: parent.width; key: "lang"; label: "Traducir al idioma (c\u00f3digo de DeepL: ES, EN-US, PT-BR\u2026)" }
        EditorField {
            id: keyField
            width: parent.width
            key: "apikey"
            label: lyrics.hasKey ? "Clave de DeepL (ya hay una guardada; escribe otra para reemplazarla)" : "Clave de DeepL"
            echoMode: TextInput.Password
        }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 11
            text: "La clave se guarda en el llavero del sistema (no en un archivo). Si tu sistema no tiene llavero, define la variable de entorno SONOTECA_DEEPL_KEY."
        }
        Row {
            spacing: 16
            Text {
                text: "Conseguir una clave"
                color: Theme.accent
                font.pixelSize: 12
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Qt.openUrlExternally("https://www.deepl.com/pro-api") }
            }
            Text {
                visible: lyrics.hasKey
                text: "Quitar la clave guardada"
                color: "#ff6b6b"
                font.pixelSize: 12
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: lyrics.clearApiKey() }
            }
        }
        Text { width: parent.width; visible: root.error !== ""; text: root.error; color: "#ff6b6b"; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton { label: "Guardar"; primary: true; onClicked: root.save() }
        }
    }
}
