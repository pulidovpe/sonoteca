pragma Singleton
import QtQuick

// Bus de navegación: las filas de canciones piden ir a un álbum sin conocer la página que las contiene (Main escucha)
QtObject {
    signal albumRequested(int albumId)
}
