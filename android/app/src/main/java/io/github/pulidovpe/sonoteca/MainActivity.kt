package io.github.pulidovpe.sonoteca

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import io.github.pulidovpe.sonoteca.db.AlbumRow
import io.github.pulidovpe.sonoteca.db.ArtistRow
import io.github.pulidovpe.sonoteca.db.PlayableTrack
import io.github.pulidovpe.sonoteca.db.PlaylistRow
import io.github.pulidovpe.sonoteca.download.DownloadPlan
import io.github.pulidovpe.sonoteca.download.DownloadProgress
import io.github.pulidovpe.sonoteca.download.formatBytes
import io.github.pulidovpe.sonoteca.playback.PlaybackModes
import io.github.pulidovpe.sonoteca.playback.PlaybackQueue
import io.github.pulidovpe.sonoteca.playback.PlayerUi
import androidx.activity.SystemBarStyle
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import io.github.pulidovpe.sonoteca.ui.Neon
import io.github.pulidovpe.sonoteca.ui.NeonIcons
import io.github.pulidovpe.sonoteca.ui.PathIcon
import io.github.pulidovpe.sonoteca.ui.SonotecaTheme
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.res.painterResource
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.ui.text.style.TextOverflow
import io.github.pulidovpe.sonoteca.cover.CoverKeys
import io.github.pulidovpe.sonoteca.cover.CoverLoader
import io.github.pulidovpe.sonoteca.ui.CoverThumb
import androidx.compose.foundation.layout.aspectRatio
import io.github.pulidovpe.sonoteca.db.CoverSample
import io.github.pulidovpe.sonoteca.ui.PlaylistCollage
import androidx.compose.foundation.lazy.grid.itemsIndexed as gridItemsIndexed

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels()

    // Android 13+: sin este permiso la reproducción funciona, pero no se ve la notificación con los controles.
    private val notificationPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    private fun askNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // tema «Neón» siempre oscuro: barras del sistema transparentes con iconos claros
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
        )
        setContent {
            SonotecaTheme {
                Surface(modifier = Modifier.fillMaxSize()) { SonotecaApp(viewModel, onBeforePlay = this::askNotificationPermission) }
            }
        }
    }
}

/** Logo y nombre de la app, arriba de todas las pantallas. */
@Composable
private fun BrandHeader() {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Image(painter = painterResource(R.drawable.sonoteca_logo), contentDescription = "Logo de Sonoteca", modifier = Modifier.size(36.dp))
        Text("Sonoteca", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    }
}

/** Destinos de la barra de navegación inferior (iconos del escritorio). */
private enum class Dest(val label: String, val icon: String) {
    Library("Biblioteca", NeonIcons.ALBUM),
    Downloaded("Descargado", NeonIcons.HEADPHONES),
    Desktop("Escritorio", NeonIcons.DISPLAY),
}

@Composable
fun SonotecaApp(viewModel: MainViewModel, onBeforePlay: () -> Unit) {
    val pairing by viewModel.pairing.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val message by viewModel.message.collectAsState()
    val artists by viewModel.artists.collectAsState()
    val tracks by viewModel.trackCount.collectAsState()
    val playlists by viewModel.playlistCount.collectAsState()
    val albums by viewModel.albums.collectAsState()
    val playlistRows by viewModel.playlistRows.collectAsState()
    val deleteAsk by viewModel.deleteAsk.collectAsState()
    val plan by viewModel.plan.collectAsState()
    val progress by viewModel.progress.collectAsState()
    val playable by viewModel.playable.collectAsState()
    val pendingPlays by viewModel.pendingPlays.collectAsState()
    val gridView by viewModel.gridView.collectAsState()
    val playerState by viewModel.playerState.collectAsState()
    var showPair by rememberSaveable { mutableStateOf(false) }
    var showQueue by rememberSaveable { mutableStateOf(false) }

    val hasCatalog = pairing != null || tracks > 0
    var dest by rememberSaveable { mutableStateOf(Dest.Library) }

    Scaffold(
        bottomBar = {
            Column {
                if (playerState.hasItem) {
                    MiniPlayer(
                        state = playerState,
                        onToggle = viewModel.player::togglePlay,
                        onPrevious = viewModel.player::previous,
                        onNext = viewModel.player::next,
                        onSeek = viewModel.player::seekTo,
                        onShuffle = viewModel.player::toggleShuffle,
                        onRepeat = viewModel.player::cycleRepeat,
                        onQueue = { showQueue = true },
                    )
                }
                if (hasCatalog) {
                    HorizontalDivider()
                    NavigationBar {
                        Dest.entries.forEach { item ->
                            NavigationBarItem(
                                selected = dest == item,
                                onClick = { dest = item },
                                icon = { PathIcon(item.icon) },
                                label = { Text(item.label) },
                            )
                        }
                    }
                }
            }
        },
    ) { padding ->
        Column(
            modifier = Modifier.padding(padding).padding(start = 16.dp, end = 16.dp, top = 16.dp).fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            BrandHeader()
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
            if (!hasCatalog) {
                // instalación nueva: aún no hay catálogo, solo se puede emparejar
                PairScreen(busy = busy, onPair = viewModel::pair)
            } else {
                // con catálogo se usa la biblioteca aunque no haya emparejamiento: lo descargado se reproduce sin servidor
                when (dest) {
                    Dest.Library -> LibraryTab(
                        covers = viewModel.covers,
                        loadSamples = viewModel::playlistCovers,
                        grid = gridView,
                        onGrid = viewModel::setGridView,
                        artists = artists,
                        albums = albums,
                        playlistRows = playlistRows,
                        busy = busy,
                        onSelect = viewModel::choose,
                    )
                    Dest.Downloaded -> DownloadedTab(
                        covers = viewModel.covers,
                        grid = gridView,
                        onGrid = viewModel::setGridView,
                        playable = playable,
                        onPlay = { index ->
                            onBeforePlay()
                            viewModel.playFromList(index)
                        },
                        onQueueTrack = { index, next ->
                            onBeforePlay()
                            viewModel.queueTrack(index, next)
                        },
                    )
                    Dest.Desktop -> DesktopTab(
                        server = current?.let { "${it.host}:${it.port}" },
                        pendingPlays = pendingPlays,
                        tracks = tracks,
                        playlists = playlists,
                        artists = artists.size,
                        albums = albums.size,
                        busy = busy,
                        onSync = viewModel::sync,
                        onUnpair = viewModel::unpair,
                        onPairRequest = { showPair = true },
                    )
                }
            }
        }
    }
    if (showQueue && playerState.hasItem) {
        QueueSheet(
            state = playerState,
            onDismiss = { showQueue = false },
            onJump = viewModel.player::jumpTo,
            onRemove = viewModel.player::removeAt,
            onClear = viewModel.player::clearQueue,
        )
    }
    plan?.let { chosen ->
        AlertDialog(
            onDismissRequest = viewModel::dismissPlan,
            title = { Text(chosen.label) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(planText(chosen))
                    if (chosen.onPhone > 0) {
                        TextButton(
                            onClick = {
                                onBeforePlay()
                                viewModel.playSelection()
                            },
                        ) { Text("Reproducir las ${chosen.onPhone} descargadas") }
                        TextButton(
                            onClick = {
                                onBeforePlay()
                                viewModel.queueSelection(next = true)
                            },
                        ) { Text("Reproducir a continuación") }
                        TextButton(
                            onClick = {
                                onBeforePlay()
                                viewModel.queueSelection(next = false)
                            },
                        ) { Text("Agregar al final de la cola") }
                        TextButton(onClick = viewModel::askDelete) { Text("Borrar ${chosen.onPhone} descargadas del teléfono") }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = viewModel::startDownload, enabled = chosen.pending.isNotEmpty() && chosen.fits && pairing != null) {
                    Text("Descargar")
                }
            },
            dismissButton = { TextButton(onClick = viewModel::dismissPlan) { Text("Cancelar") } },
        )
    }
    if (showPair && pairing == null) {
        AlertDialog(
            onDismissRequest = { showPair = false },
            title = { Text("Emparejar con el escritorio") },
            text = { PairScreen(busy = busy, onPair = viewModel::pair) },
            confirmButton = {},
            dismissButton = { TextButton(onClick = { showPair = false }) { Text("Cerrar") } },
        )
    }
    deleteAsk?.let { ask ->
        AlertDialog(
            onDismissRequest = viewModel::dismissDelete,
            title = { Text("¿Borrar del teléfono?") },
            text = {
                Text("Se borrarán ${ask.count} pistas de «${ask.selection.label}» de Música/Sonoteca. Tu escritorio y tu catálogo no se tocan.")
            },
            confirmButton = { TextButton(onClick = viewModel::confirmDelete) { Text("Borrar") } },
            dismissButton = { TextButton(onClick = viewModel::dismissDelete) { Text("Cancelar") } },
        )
    }
}

private fun planText(plan: DownloadPlan): String = when {
    plan.pending.isEmpty() && plan.notReady == 0 -> "Las ${plan.totalTracks} pistas ya están descargadas."
    plan.pending.isEmpty() -> "No hay nada que descargar ahora: ${plan.notReady} pistas aún no están listas en el escritorio (calcula su huella); sincroniza otra vez en unos minutos."
    else -> buildString {
        append("Faltan ${plan.pending.size} de ${plan.totalTracks} pistas (${formatBytes(plan.pendingBytes)}).")
        if (plan.replacing > 0) append(" ${plan.replacing} cambiaron en el escritorio y se bajarán de nuevo.")
        append("\nEspacio libre en el teléfono: ${formatBytes(plan.freeBytes)}.")
        if (!plan.fits) append("\nNo hay espacio suficiente (se deja un margen de 200 MB).")
        append("\nSe guardarán en Música/Sonoteca.")
        if (plan.notReady > 0) append("\n${plan.notReady} pistas más aún no están listas en el escritorio: sincroniza otra vez en unos minutos.")
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

/** Una fila de la biblioteca (artista, álbum o lista), con su portada, que se ve igual en lista y en cuadrícula. */
private class LibraryItem(
    val key: String,
    val title: String,
    val subtitle: String?,
    val right: String,
    val onClick: () -> Unit,
    val cover: @Composable (Modifier) -> Unit,
)

/** Selector Lista / Cuadrícula (se recuerda entre sesiones). */
@Composable
private fun ViewModeChips(grid: Boolean, onGrid: (Boolean) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        FilterChip(selected = !grid, onClick = { onGrid(false) }, label = { Text("Lista", maxLines = 1) })
        FilterChip(selected = grid, onClick = { onGrid(true) }, label = { Text("Cuadrícula", maxLines = 1) })
    }
}

@Composable
private fun LibraryTab(
    covers: CoverLoader,
    loadSamples: suspend (String) -> List<CoverSample>,
    grid: Boolean,
    onGrid: (Boolean) -> Unit,
    artists: List<ArtistRow>,
    albums: List<AlbumRow>,
    playlistRows: List<PlaylistRow>,
    busy: Boolean,
    onSelect: (Selection) -> Unit,
) {
    var tab by rememberSaveable { mutableStateOf(0) }
    // en color lo que está completo en el teléfono; en gris lo que aún falta por descargar (también si está a medias)
    val entries = remember(tab, artists, albums, playlistRows) {
        when (tab) {
            0 -> artists.map { artist ->
                LibraryItem(
                    key = artist.name,
                    title = artist.name.ifEmpty { "(sin artista)" },
                    subtitle = null,
                    right = "${artist.downloaded}/${artist.tracks}",
                    onClick = { onSelect(Selection.Artist(artist.name)) },
                    cover = { modifier ->
                        CoverThumb(
                            covers, CoverKeys.artist(artist.name), artist.sampleUuid, artist = true, modifier = modifier,
                            colored = artist.tracks > 0 && artist.downloaded >= artist.tracks,
                        )
                    },
                )
            }
            1 -> albums.map { album ->
                LibraryItem(
                    key = album.artist + "||" + album.album,
                    title = album.album.ifEmpty { "(sin álbum)" },
                    subtitle = album.artist.ifEmpty { "(sin artista)" },
                    right = "${album.downloaded}/${album.tracks}",
                    onClick = { onSelect(Selection.Album(album.artist, album.album)) },
                    cover = { modifier ->
                        CoverThumb(
                            covers, CoverKeys.album(album.artist, album.album), album.sampleUuid, artist = false, modifier = modifier,
                            colored = album.tracks > 0 && album.downloaded >= album.tracks,
                        )
                    },
                )
            }
            else -> playlistRows.map { list ->
                LibraryItem(
                    key = list.uuid,
                    title = list.name,
                    subtitle = null,
                    right = "${list.downloaded}/${list.tracks}",
                    onClick = { onSelect(Selection.Playlist(list.uuid, list.name)) },
                    cover = { modifier ->
                        PlaylistCollage(covers, list.uuid, loadSamples, modifier = modifier, colored = list.tracks > 0 && list.downloaded >= list.tracks)
                    },
                )
            }
        }
    }
    Column(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Biblioteca", style = MaterialTheme.typography.headlineSmall)
        // tres pestañas de igual ancho y con poco relleno
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            val tabPadding = PaddingValues(horizontal = 4.dp)
            listOf("Artistas", "Álbumes", "Listas").forEachIndexed { index, title ->
                if (tab == index) {
                    Button(onClick = { tab = index }, modifier = Modifier.weight(1f), contentPadding = tabPadding) {
                        Text(title, style = MaterialTheme.typography.labelMedium, maxLines = 1)
                    }
                } else {
                    TextButton(onClick = { tab = index }, modifier = Modifier.weight(1f), contentPadding = tabPadding) {
                        Text(title, style = MaterialTheme.typography.labelMedium, maxLines = 1)
                    }
                }
            }
        }
        ViewModeChips(grid = grid, onGrid = onGrid)
        HorizontalDivider()
        if (grid) {
            LazyVerticalGrid(
                columns = GridCells.Fixed(3),
                modifier = Modifier.weight(1f),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                gridItems(entries, key = { it.key }) { entry -> GridCell(entry, enabled = !busy) }
            }
        } else {
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(entries, key = { it.key }) { entry ->
                    SelectableRow(
                        title = entry.title,
                        subtitle = entry.subtitle,
                        right = entry.right,
                        enabled = !busy,
                        onClick = entry.onClick,
                        leading = { entry.cover(Modifier.size(48.dp)) },
                    )
                }
            }
        }
    }
}

/** Celda de la cuadrícula (3 columnas): la portada cuadrada, el nombre debajo y cuántas pistas están en el teléfono. */
@Composable
private fun GridCell(entry: LibraryItem, enabled: Boolean) {
    Column(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).clickable(enabled = enabled) { entry.onClick() },
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        entry.cover(Modifier.fillMaxWidth().aspectRatio(1f))
        Text(entry.title, style = MaterialTheme.typography.bodySmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
        if (entry.subtitle != null) Text(entry.subtitle, style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(entry.right, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun DownloadedTab(
    covers: CoverLoader,
    grid: Boolean,
    onGrid: (Boolean) -> Unit,
    playable: List<PlayableTrack>,
    onPlay: (Int) -> Unit,
    onQueueTrack: (Int, Boolean) -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Descargado", style = MaterialTheme.typography.headlineSmall)
        Text("${playable.size} pistas en el teléfono", style = MaterialTheme.typography.bodySmall)
        ViewModeChips(grid = grid, onGrid = onGrid)
        HorizontalDivider()
        if (playable.isEmpty()) {
            Text(
                "Aún no has descargado música. En Biblioteca elige un artista, álbum o lista y pulsa «Descargar».",
                modifier = Modifier.padding(vertical = 12.dp),
            )
        } else if (grid) {
            LazyVerticalGrid(
                columns = GridCells.Fixed(3),
                modifier = Modifier.weight(1f),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                gridItemsIndexed(playable, key = { _, track -> track.uuid }) { index, track ->
                    DownloadedGridCell(
                        track = track,
                        covers = covers,
                        onPlay = { onPlay(index) },
                        onQueueNext = { onQueueTrack(index, true) },
                        onQueueEnd = { onQueueTrack(index, false) },
                    )
                }
            }
        } else {
            LazyColumn(modifier = Modifier.weight(1f)) {
                itemsIndexed(playable, key = { _, track -> track.uuid }) { index, track ->
                    DownloadedRow(
                        track = track,
                        covers = covers,
                        onPlay = { onPlay(index) },
                        onQueueNext = { onQueueTrack(index, true) },
                        onQueueEnd = { onQueueTrack(index, false) },
                    )
                }
            }
        }
    }
}

@Composable
private fun DesktopTab(
    server: String?,
    pendingPlays: Int,
    tracks: Int,
    playlists: Int,
    artists: Int,
    albums: Int,
    busy: Boolean,
    onSync: () -> Unit,
    onUnpair: () -> Unit,
    onPairRequest: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Escritorio", style = MaterialTheme.typography.headlineSmall)
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(if (server != null) "Emparejado con $server" else "Sin emparejar: lo descargado se reproduce igual, sin servidor.")
                Text("$tracks pistas · $playlists listas · $artists artistas · $albums álbumes", style = MaterialTheme.typography.bodySmall)
                if (pendingPlays > 0) {
                    Text("$pendingPlays reproducciones por subir al escritorio (se envían al conectar).", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (server != null) {
                Button(onClick = onSync, enabled = !busy) { Text(if (busy) "Sincronizando…" else "Sincronizar catálogo") }
                TextButton(onClick = onUnpair, enabled = !busy) { Text("Olvidar") }
            } else {
                Button(onClick = onPairRequest, enabled = !busy) { Text("Emparejar") }
            }
        }
    }
}

@Composable
private fun SelectableRow(
    title: String,
    subtitle: String?,
    right: String,
    enabled: Boolean,
    onClick: () -> Unit,
    leading: (@Composable () -> Unit)? = null,
) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled) { onClick() }.padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        leading?.invoke()
        Column(modifier = Modifier.weight(1f)) {
            Text(title)
            if (subtitle != null) Text(subtitle, style = MaterialTheme.typography.bodySmall)
        }
        Text(right)
    }
}

@Composable
private fun MiniPlayer(
    state: PlayerUi,
    onToggle: () -> Unit,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onSeek: (Long) -> Unit,
    onShuffle: () -> Unit,
    onRepeat: () -> Unit,
    onQueue: () -> Unit,
) {
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs.coerceAtLeast(1L)
    Surface(
        color = MaterialTheme.colorScheme.surfaceContainerHighest,
        shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
            Text(state.title.ifEmpty { "(sin título)" }, style = MaterialTheme.typography.titleMedium, maxLines = 1)
            if (state.artist.isNotEmpty()) Text(state.artist, style = MaterialTheme.typography.bodySmall, maxLines = 1)
            state.error?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error) }
            Slider(
                value = dragging ?: state.positionMs.coerceIn(0L, duration).toFloat(),
                onValueChange = { dragging = it },
                onValueChangeFinished = {
                    dragging?.let { onSeek(it.toLong()) }
                    dragging = null
                },
                valueRange = 0f..duration.toFloat(),
            )
            Text(
                PlaybackQueue.formatTime((dragging ?: state.positionMs.toFloat()).toLong()) + " / " + PlaybackQueue.formatTime(state.durationMs),
                style = MaterialTheme.typography.bodySmall,
            )
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onPrevious) { PathIcon(NeonIcons.PREV, description = "Anterior") }
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .clip(CircleShape)
                        .background(Neon.playGradient)
                        .clickable(onClick = onToggle)
                        .semantics { contentDescription = if (state.isPlaying) "Pausar" else "Reproducir" },
                    contentAlignment = Alignment.Center,
                ) {
                    PathIcon(if (state.isPlaying) NeonIcons.PAUSE else NeonIcons.PLAY, size = 28.dp, tint = Neon.textOnAccent)
                }
                IconButton(onClick = onNext, enabled = state.hasNext) { PathIcon(NeonIcons.NEXT, description = "Siguiente") }
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                FilterChip(selected = state.shuffle, onClick = onShuffle, label = { Text("Aleatorio", maxLines = 1) })
                FilterChip(
                    selected = state.repeatMode != PlaybackModes.REPEAT_OFF,
                    onClick = onRepeat,
                    label = { Text(PlaybackModes.repeatLabel(state.repeatMode), maxLines = 1) },
                )
                AssistChip(onClick = onQueue, label = { Text("Cola (${state.queue.size})", maxLines = 1) })
            }
        }
    }
}

/** Menú ⋮ de una pista descargada: ponerla a continuación o al final de la cola. */
@Composable
private fun TrackMenu(onQueueNext: () -> Unit, onQueueEnd: () -> Unit) {
    var menu by remember { mutableStateOf(false) }
    Box {
        TextButton(onClick = { menu = true }, contentPadding = PaddingValues(0.dp), modifier = Modifier.size(36.dp)) { Text("⋮") }
        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
            DropdownMenuItem(text = { Text("Reproducir a continuación") }, onClick = { menu = false; onQueueNext() })
            DropdownMenuItem(text = { Text("Agregar al final de la cola") }, onClick = { menu = false; onQueueEnd() })
        }
    }
}

/** Una pista de la pestaña «Descargado» en lista: la portada de su álbum, tocar la reproduce; el menú ⋮ la pone en la cola. */
@Composable
private fun DownloadedRow(track: PlayableTrack, covers: CoverLoader, onPlay: () -> Unit, onQueueNext: () -> Unit, onQueueEnd: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        CoverThumb(covers, CoverKeys.album(track.albumArtist, track.album), track.uuid, artist = false, modifier = Modifier.size(48.dp))
        Column(modifier = Modifier.weight(1f).clickable { onPlay() }.padding(vertical = 4.dp)) {
            Text(track.title.ifEmpty { "(sin título)" }, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                (track.artist.ifEmpty { track.albumArtist }).ifEmpty { "(sin artista)" } + " · " + track.album.ifEmpty { "(sin álbum)" },
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Text(PlaybackQueue.formatTime((track.duration * 1000).toLong()))
        TrackMenu(onQueueNext, onQueueEnd)
    }
}

/** Una pista descargada en cuadrícula: la portada de su álbum, el título y el artista debajo, y el menú ⋮. */
@Composable
private fun DownloadedGridCell(track: PlayableTrack, covers: CoverLoader, onPlay: () -> Unit, onQueueNext: () -> Unit, onQueueEnd: () -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        CoverThumb(
            covers, CoverKeys.album(track.albumArtist, track.album), track.uuid, artist = false,
            modifier = Modifier.fillMaxWidth().aspectRatio(1f).clickable { onPlay() },
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f).clickable { onPlay() }) {
                Text(track.title.ifEmpty { "(sin título)" }, style = MaterialTheme.typography.bodySmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(
                    (track.artist.ifEmpty { track.albumArtist }).ifEmpty { "(sin artista)" },
                    style = MaterialTheme.typography.labelSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            TrackMenu(onQueueNext, onQueueEnd)
        }
    }
}

/** La cola de reproducción («Reproduciendo»): tocar una pista salta a ella; «Quitar» la saca (no la que suena); «Vaciar» deja solo la que suena. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun QueueSheet(state: PlayerUi, onDismiss: () -> Unit, onJump: (Int) -> Unit, onRemove: (Int) -> Unit, onClear: () -> Unit) {
    val listState = rememberLazyListState(initialFirstVisibleItemIndex = state.currentIndex.coerceAtLeast(0))
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Reproduciendo (${state.queue.size})", style = MaterialTheme.typography.titleMedium)
            TextButton(onClick = onClear, enabled = state.queue.size > 1) { Text("Vaciar") }
        }
        LazyColumn(state = listState, modifier = Modifier.padding(horizontal = 16.dp)) {
            itemsIndexed(state.queue, key = { index, item -> "$index-${item.uuid}" }) { index, item ->
                val current = index == state.currentIndex
                Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f).clickable { onJump(index) }.padding(vertical = 8.dp)) {
                        Text(
                            item.title.ifEmpty { "(sin título)" },
                            color = if (current) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                            fontWeight = if (current) FontWeight.Bold else FontWeight.Normal,
                            maxLines = 1,
                        )
                        if (item.artist.isNotEmpty()) Text(item.artist, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                    }
                    TextButton(onClick = { onRemove(index) }, enabled = !current) { Text("Quitar") }
                }
            }
        }
    }
}
