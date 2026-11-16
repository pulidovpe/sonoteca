package io.github.pulidovpe.sonoteca

import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.github.pulidovpe.sonoteca.db.ArtistRow
import io.github.pulidovpe.sonoteca.download.DownloadPlan
import io.github.pulidovpe.sonoteca.download.DownloadProgress
import io.github.pulidovpe.sonoteca.download.formatBytes

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme(colorScheme = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()) {
                Surface(modifier = Modifier.fillMaxSize()) { SonotecaApp(viewModel) }
            }
        }
    }
}

@Composable
fun SonotecaApp(viewModel: MainViewModel) {
    val pairing by viewModel.pairing.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val message by viewModel.message.collectAsState()
    val artists by viewModel.artists.collectAsState()
    val tracks by viewModel.trackCount.collectAsState()
    val playlists by viewModel.playlistCount.collectAsState()
    val plan by viewModel.plan.collectAsState()
    val progress by viewModel.progress.collectAsState()

    Scaffold { padding ->
        Column(
            modifier = Modifier.padding(padding).padding(16.dp).fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Sonoteca", style = MaterialTheme.typography.headlineMedium)
            message?.let { text ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(text)
                        TextButton(onClick = viewModel::dismissMessage) { Text("Cerrar") }
                    }
                }
            }
            progress?.let { DownloadCard(it, onCancel = viewModel::cancelDownload) }
            val current = pairing
            if (current == null) {
                PairScreen(busy = busy, onPair = viewModel::pair)
            } else {
                LibraryScreen(
                    server = "${current.host}:${current.port}",
                    tracks = tracks,
                    playlists = playlists,
                    artists = artists,
                    busy = busy,
                    onSync = viewModel::sync,
                    onUnpair = viewModel::unpair,
                    onArtist = viewModel::planArtist,
                )
            }
        }
    }
    plan?.let { chosen ->
        AlertDialog(
            onDismissRequest = viewModel::dismissPlan,
            title = { Text(chosen.label) },
            text = { Text(planText(chosen)) },
            confirmButton = {
                TextButton(onClick = viewModel::startDownload, enabled = chosen.pending.isNotEmpty() && chosen.fits) {
                    Text("Descargar")
                }
            },
            dismissButton = { TextButton(onClick = viewModel::dismissPlan) { Text("Cancelar") } },
        )
    }
}

private fun planText(plan: DownloadPlan): String = when {
    plan.pending.isEmpty() -> "Las ${plan.totalTracks} pistas ya están descargadas."
    else -> buildString {
        append("Faltan ${plan.pending.size} de ${plan.totalTracks} pistas (${formatBytes(plan.pendingBytes)}).")
        if (plan.replacing > 0) append(" ${plan.replacing} cambiaron en el escritorio y se bajarán de nuevo.")
        append("\nEspacio libre en el teléfono: ${formatBytes(plan.freeBytes)}.")
        if (!plan.fits) append("\nNo hay espacio suficiente (se deja un margen de 200 MB).")
        append("\nSe guardarán en Música/Sonoteca.")
    }
}

@Composable
private fun DownloadCard(progress: DownloadProgress, onCancel: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            val position = (progress.doneTracks + 1).coerceAtMost(progress.totalTracks)
            Text("Descargando $position de ${progress.totalTracks}: ${progress.currentTitle}")
            LinearProgressIndicator(progress = { progress.fraction }, modifier = Modifier.fillMaxWidth())
            Text("${formatBytes(progress.bytesDone)} de ${formatBytes(progress.bytesTotal)}")
            TextButton(onClick = onCancel) { Text("Cancelar") }
        }
    }
}

@Composable
private fun PairScreen(busy: Boolean, onPair: (String, String) -> Unit) {
    var url by rememberSaveable { mutableStateOf("") }
    var name by rememberSaveable { mutableStateOf(Build.MODEL) }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("En el escritorio ejecuta «sonoteca sync-serve» y pega aquí la URL que muestra (Wi-Fi o USB).")
        OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            label = { Text("URL de emparejamiento") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 3,
        )
        OutlinedTextField(
            value = name,
            onValueChange = { name = it },
            label = { Text("Nombre de este móvil") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Button(onClick = { onPair(url, name) }, enabled = !busy && url.isNotBlank()) {
            Text(if (busy) "Emparejando…" else "Emparejar")
        }
    }
}

@Composable
private fun LibraryScreen(
    server: String,
    tracks: Int,
    playlists: Int,
    artists: List<ArtistRow>,
    busy: Boolean,
    onSync: () -> Unit,
    onUnpair: () -> Unit,
    onArtist: (String) -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Escritorio: $server")
        Text("$tracks pistas · $playlists listas · ${artists.size} artistas")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = onSync, enabled = !busy) { Text(if (busy) "Sincronizando…" else "Sincronizar catálogo") }
            TextButton(onClick = onUnpair, enabled = !busy) { Text("Olvidar") }
        }
        HorizontalDivider()
        LazyColumn(modifier = Modifier.weight(1f)) {
            items(artists, key = { it.name }) { artist ->
                Row(
                    modifier = Modifier.fillMaxWidth().clickable(enabled = !busy) { onArtist(artist.name) }.padding(vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(artist.name.ifEmpty { "(sin artista)" })
                    Text("${artist.downloaded}/${artist.tracks}")
                }
            }
        }
    }
}
