package io.github.pulidovpe.sonoteca.net

import org.json.JSONObject

/** Manifiesto de sincronización (docs/SYNC.md). Los campos que el escritorio puede mandar como null llegan como 0 o "". */
data class ManifestTrack(
    val uuid: String,
    val hash: String,
    val size: Long,
    val format: String,
    val title: String,
    val artist: String,
    val albumArtist: String,
    val album: String,
    val trackNo: Int,
    val discNo: Int,
    val year: Int,
    val duration: Double,
    val genre: String,
    val hasCover: Boolean,
    val hasLyrics: Boolean,
)

data class ManifestPlaylist(val uuid: String, val name: String, val updatedAt: String, val tracks: List<String>)

data class DeletedPlaylist(val uuid: String, val deletedAt: String)

data class Manifest(
    val api: Int,
    val schema: Int,
    val generatedAt: String,
    val pendingHash: Int,
    val tracks: List<ManifestTrack>,
    val playlists: List<ManifestPlaylist>,
    val deletedPlaylists: List<DeletedPlaylist>,
    /** El manifiesto trae TODAS las pistas (aunque sin huella): se puede borrar con seguridad lo que no aparece. Servidores antiguos: false. */
    val complete: Boolean = false,
)

// `isNull` es true si la clave falta o vale null; con org.json, optString sobre un null devolvería el texto "null".
private fun JSONObject.text(name: String): String = if (isNull(name)) "" else getString(name)
private fun JSONObject.int(name: String): Int = if (isNull(name)) 0 else getInt(name)

fun parseManifest(json: String): Manifest {
    val root = JSONObject(json)
    val tracks = root.getJSONArray("tracks").let { array ->
        List(array.length()) { i ->
            val t = array.getJSONObject(i)
            ManifestTrack(
                uuid = t.getString("uuid"),
                hash = t.text("hash"),   // null mientras el escritorio aún calcula la huella
                size = if (t.isNull("size")) 0L else t.getLong("size"),
                format = t.text("format"),
                title = t.text("title"),
                artist = t.text("artist"),
                albumArtist = t.text("album_artist"),
                album = t.text("album"),
                trackNo = t.int("track_no"),
                discNo = t.int("disc_no"),
                year = t.int("year"),
                duration = if (t.isNull("duration")) 0.0 else t.getDouble("duration"),
                genre = t.text("genre"),
                hasCover = !t.isNull("has_cover") && t.getBoolean("has_cover"),
                hasLyrics = !t.isNull("has_lyrics") && t.getBoolean("has_lyrics"),
            )
        }
    }
    val playlists = root.getJSONArray("playlists").let { array ->
        List(array.length()) { i ->
            val p = array.getJSONObject(i)
            val uuids = p.getJSONArray("tracks")
            ManifestPlaylist(
                uuid = p.getString("uuid"),
                name = p.getString("name"),
                updatedAt = p.getString("updated_at"),
                tracks = List(uuids.length()) { j -> uuids.getString(j) },
            )
        }
    }
    val deleted = root.getJSONArray("deleted_playlists").let { array ->
        List(array.length()) { i ->
            val d = array.getJSONObject(i)
            DeletedPlaylist(d.getString("uuid"), d.getString("deleted_at"))
        }
    }
    return Manifest(
        api = root.getInt("api"),
        schema = root.int("schema"),
        generatedAt = root.text("generated_at"),
        pendingHash = root.int("pending_hash"),
        complete = !root.isNull("complete") && root.getBoolean("complete"),
        tracks = tracks,
        playlists = playlists,
        deletedPlaylists = deleted,
    )
}
