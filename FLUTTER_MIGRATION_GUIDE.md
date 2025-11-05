# Flutter Migration Guide - SAM-FTP CLI

**Version:** 1.0
**Target Platform:** Flutter (iOS, Android, Web, Desktop)
**Source Application:** SAM-FTP CLI (Python)

---

## Table of Contents

1. [Application Overview](#1-application-overview)
2. [Architecture & Design Patterns](#2-architecture--design-patterns)
3. [Data Models](#3-data-models)
4. [Core Features](#4-core-features)
5. [Network Layer](#5-network-layer)
6. [State Management](#6-state-management)
7. [UI/UX Design](#7-uiux-design)
8. [Caching System](#8-caching-system)
9. [Bookmarks System](#9-bookmarks-system)
10. [Media Player Integration](#10-media-player-integration)
11. [Configuration Management](#11-configuration-management)
12. [Error Handling & Logging](#12-error-handling--logging)
13. [Flutter Packages Recommendations](#13-flutter-packages-recommendations)
14. [Migration Strategy](#14-migration-strategy)
15. [Implementation Checklist](#15-implementation-checklist)

---

## 1. Application Overview

### What is SAM-FTP CLI?

SAM-FTP CLI is a media browsing application that allows users to:
- Browse HTTP-based FTP servers (specifically SAM-FTP servers)
- Stream/play media files (videos, audio, images)
- Download files and folders
- Bookmark favorite directories
- Search and filter content
- Multi-select files for batch operations

### Core Value Proposition

- **Async Operations**: Non-blocking I/O for smooth UX
- **Rich Caching**: TTL-based caching for performance
- **Bookmarks**: Quick access to frequently accessed directories
- **Multi-server Support**: Manage multiple FTP servers
- **Batch Operations**: Select multiple files for download/playback
- **Background Playback**: Continue browsing while media plays

### Key Technologies (Python)

- **aiohttp**: Async HTTP client
- **BeautifulSoup**: HTML parsing
- **Rich**: Terminal UI library
- **Click**: CLI framework
- **platformdirs**: Cross-platform directory paths

---

## 2. Architecture & Design Patterns

### Current Architecture (Python)

```
┌─────────────────────────────────────────────────────────┐
│                      main.py                             │
│              (Entry Point + Click CLI)                   │
└─────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   AppSession                             │
│          (Runtime State Container)                       │
│  - selected_server                                       │
│  - selected_player                                       │
│  - download_directory                                    │
│  - history (navigation stack)                            │
│  - current_url                                          │
└─────────────────────────────────────────────────────────┘
                           ▼
         ┌─────────────────┴─────────────────┐
         ▼                                    ▼
┌──────────────────┐              ┌────────────────────┐
│  ftp_client.py   │              │      ui.py         │
│  (HTTP Client)   │              │  (UI Layer)        │
│                  │              │                    │
│ - fetch_html     │              │ - browse_directory │
│ - parse_html     │              │ - display_listing  │
│ - download_file  │              │ - batch_selection  │
│ - retry logic    │              │ - breadcrumb       │
└──────────────────┘              └────────────────────┘
         │                                    │
         ▼                                    ▼
┌──────────────────┐              ┌────────────────────┐
│   cache.py       │              │   bookmarks.py     │
│  (CacheManager)  │              │(BookmarkManager)   │
│                  │              │                    │
│ - TTL-based      │              │ - CRUD operations  │
│ - Memory + Disk  │              │ - JSON storage     │
└──────────────────┘              └────────────────────┘
         │                                    │
         ▼                                    ▼
┌──────────────────┐              ┌────────────────────┐
│   config.py      │              │   player.py        │
│(ConfigManager)   │              │(Media Player)      │
│                  │              │                    │
│ - .env parsing   │              │ - mpv/VLC/IINA     │
│ - validation     │              │ - playlist mgmt    │
│ - wizard         │              │ - background play  │
└──────────────────┘              └────────────────────┘
```

### Recommended Flutter Architecture

Use **Clean Architecture** with **BLoC/Riverpod** for state management:

```
lib/
├── core/
│   ├── constants/
│   ├── errors/
│   ├── network/
│   ├── utils/
│   └── platform/
├── features/
│   ├── authentication/
│   ├── server_selection/
│   ├── file_browser/
│   │   ├── data/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── datasources/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── repositories/
│   │   │   └── usecases/
│   │   └── presentation/
│   │       ├── blocs/
│   │       ├── widgets/
│   │       └── screens/
│   ├── media_player/
│   ├── downloads/
│   ├── bookmarks/
│   ├── search/
│   └── settings/
└── main.dart
```

### Key Design Patterns

1. **Repository Pattern**: Abstract data sources (network, cache, local storage)
2. **Use Case Pattern**: Each feature action is a use case
3. **Dependency Injection**: Use `get_it` or Riverpod providers
4. **Observer Pattern**: BLoC/StateNotifier for reactive UI
5. **Factory Pattern**: For creating different auth strategies, players

---

## 3. Data Models

### Core Models (from `data_models.py`)

#### Server Model

```dart
class Server {
  final String name;
  final String url;
  final String? username;
  final String? password;
  final double? lastAccessed;
  final String? preferredPlayer;

  Server({
    required this.name,
    required this.url,
    this.username,
    this.password,
    this.lastAccessed,
    this.preferredPlayer,
  });

  // Factory for JSON serialization
  factory Server.fromJson(Map<String, dynamic> json) {
    return Server(
      name: json['name'] as String,
      url: json['url'] as String,
      username: json['username'] as String?,
      password: json['password'] as String?,
      lastAccessed: json['last_accessed'] as double?,
      preferredPlayer: json['preferred_player'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'url': url,
      'username': username,
      'password': password,
      'last_accessed': lastAccessed,
      'preferred_player': preferredPlayer,
    };
  }

  // For HTTP Basic Auth
  String? get basicAuthHeader {
    if (username != null && password != null) {
      final credentials = base64Encode(utf8.encode('$username:$password'));
      return 'Basic $credentials';
    }
    return null;
  }
}
```

#### File Model

```dart
class FileItem {
  final String name;
  final String url;
  final int? sizeBytes;

  FileItem({
    required this.name,
    required this.url,
    this.sizeBytes,
  });

  // File type detection
  FileType get fileType {
    final ext = name.toLowerCase();
    if (_videoExtensions.any(ext.endsWith)) return FileType.video;
    if (_audioExtensions.any(ext.endsWith)) return FileType.audio;
    if (_imageExtensions.any(ext.endsWith)) return FileType.image;
    return FileType.other;
  }

  String get formattedSize {
    if (sizeBytes == null) return '';

    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    double size = sizeBytes!.toDouble();
    int unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return '${size.toStringAsFixed(1)} ${units[unitIndex]}';
  }
}

enum FileType { video, audio, image, other }

const _videoExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v'];
const _audioExtensions = ['.mp3', '.flac', '.m4a', '.wav', '.ogg', '.aac'];
const _imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'];
```

#### Folder Model

```dart
class Folder {
  final String name;
  final String url;

  Folder({
    required this.name,
    required this.url,
  });

  bool get isParentDirectory => name == '..';
}
```

#### Bookmark Model

```dart
class Bookmark {
  final String name;
  final String server;
  final String url;
  final DateTime timestamp;

  Bookmark({
    required this.name,
    required this.server,
    required this.url,
    required this.timestamp,
  });

  factory Bookmark.fromJson(Map<String, dynamic> json) {
    return Bookmark(
      name: json['name'] as String,
      server: json['server'] as String,
      url: json['url'] as String,
      timestamp: DateTime.fromMillisecondsSinceEpoch(
        (json['timestamp'] as num * 1000).toInt(),
      ),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'server': server,
      'url': url,
      'timestamp': timestamp.millisecondsSinceEpoch / 1000,
    };
  }
}
```

#### Cache Entry Model

```dart
class CacheEntry {
  final String url;
  final DateTime timestamp;
  final List<Folder> folders;
  final List<FileItem> files;

  CacheEntry({
    required this.url,
    required this.timestamp,
    required this.folders,
    required this.files,
  });

  bool isExpired(Duration ttl) {
    return DateTime.now().difference(timestamp) > ttl;
  }
}
```

#### App Session Model

```dart
class AppSession {
  final Server? selectedServer;
  final String? selectedPlayer;
  final String? downloadDirectory;
  final List<String> navigationHistory;
  final String? currentUrl;

  AppSession({
    this.selectedServer,
    this.selectedPlayer,
    this.downloadDirectory,
    List<String>? navigationHistory,
    this.currentUrl,
  }) : navigationHistory = navigationHistory ?? [];

  AppSession copyWith({
    Server? selectedServer,
    String? selectedPlayer,
    String? downloadDirectory,
    List<String>? navigationHistory,
    String? currentUrl,
  }) {
    return AppSession(
      selectedServer: selectedServer ?? this.selectedServer,
      selectedPlayer: selectedPlayer ?? this.selectedPlayer,
      downloadDirectory: downloadDirectory ?? this.downloadDirectory,
      navigationHistory: navigationHistory ?? this.navigationHistory,
      currentUrl: currentUrl ?? this.currentUrl,
    );
  }
}
```

---

## 4. Core Features

### 4.1 Server Management

**Functionality:**
- Add/edit/delete servers
- Test server connectivity
- Store credentials securely
- Support for HTTP Basic Auth

**Implementation Notes:**
- Use `flutter_secure_storage` for credentials
- Implement connectivity testing before saving
- Validate URL format
- Support both authenticated and public servers

### 4.2 Directory Browsing

**Functionality:**
- Fetch and parse HTML directory listings
- Navigate folders (forward/back)
- Display files and folders with icons
- Show breadcrumb navigation
- Support pull-to-refresh

**Implementation Notes:**
- Parse HTML using `html` package
- Look for `<td class="fb-n">` elements containing `<a>` tags
- Parent directory is constructed using `Uri.resolve(baseUrl, '..')`
- Maintain navigation stack for back button

### 4.3 File Operations

**Functionality:**
- Download single files
- Download multiple files (batch)
- Download with progress tracking
- Resume interrupted downloads (optional)
- Choose download location

**Implementation Notes:**
- Use `dio` for downloads with progress callbacks
- Store downloads in app documents directory or user-selected folder
- Show notification for download completion
- Support cancellation

### 4.4 Media Playback

**Functionality:**
- Play videos, audio, images
- Create playlists from multiple files
- Background playback
- Support external players (system default)
- Picture-in-Picture (PiP) mode

**Implementation Notes:**
- Use `video_player` or `better_player` for videos
- Use `just_audio` for audio
- Use `photo_view` for images
- For external players, use `url_launcher`
- Store player preference per session

### 4.5 Bookmarks

**Functionality:**
- Add current directory to bookmarks
- List all bookmarks
- Navigate to bookmarked locations
- Delete bookmarks
- Organize by server

**Implementation Notes:**
- Store bookmarks in local JSON file
- Use `path_provider` for file location
- Implement swipe-to-delete
- Show server grouping

### 4.6 Search & Filter

**Functionality:**
- Fuzzy search within current directory
- Filter by file type
- Deep search across server (optional)

**Implementation Notes:**
- Implement client-side filtering
- Use `flutter_typeahead` or `search_delegate`
- Highlight matching text

### 4.7 Batch Operations

**Functionality:**
- Select multiple files/folders
- Download selected items
- Play selected media files
- Clear selection
- Select all/none

**Implementation Notes:**
- Maintain `Set<int>` of selected indices
- Show selection indicators on items
- Provide action bar with batch actions

---

## 5. Network Layer

### HTTP Client Implementation

**Python Implementation:** `ftp_client.py`

Key features:
- Async HTTP requests using `aiohttp`
- Connection pooling (single session)
- Retry logic with exponential backoff (3 attempts: 1s, 2s, 4s)
- Custom exceptions for different error types
- HTTP Basic Auth support
- Timeout handling (30s default)

**Flutter Equivalent:**

```dart
class FtpHttpClient {
  final Dio _dio;
  final int maxRetries;
  final Duration timeout;

  FtpHttpClient({
    this.maxRetries = 3,
    this.timeout = const Duration(seconds: 30),
  }) : _dio = Dio(BaseOptions(
          connectTimeout: timeout,
          receiveTimeout: timeout,
          followRedirects: true,
        )) {
    _dio.interceptors.add(LogInterceptor(responseBody: false));
    _dio.interceptors.add(RetryInterceptor(
      dio: _dio,
      maxRetries: maxRetries,
      retryDelays: const [
        Duration(seconds: 1),
        Duration(seconds: 2),
        Duration(seconds: 4),
      ],
    ));
  }

  Future<String> fetchHtml({
    required String url,
    String? basicAuthHeader,
  }) async {
    try {
      final response = await _dio.get(
        url,
        options: Options(
          headers: basicAuthHeader != null
            ? {'Authorization': basicAuthHeader}
            : null,
        ),
      );

      return response.data as String;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  FtpClientException _handleDioError(DioException e) {
    switch (e.response?.statusCode) {
      case 401:
        return AuthenticationException('Authentication required - invalid or missing credentials');
      case 403:
        return AuthenticationException('Access forbidden - check permissions');
      case 404:
        return NotFoundException('Resource not found: ${e.requestOptions.uri}');
      case >= 500:
        return ServerException('Server error (HTTP ${e.response?.statusCode})');
      case >= 400:
        return ConnectionException('Client error (HTTP ${e.response?.statusCode})');
      default:
        if (e.type == DioExceptionType.connectionTimeout) {
          return TimeoutException('Request timeout');
        } else if (e.type == DioExceptionType.connectionError) {
          return ConnectionException('Connection failed - check network and server address');
        }
        return ConnectionException('Request error: ${e.message}');
    }
  }
}

// Custom exceptions
abstract class FtpClientException implements Exception {
  final String message;
  FtpClientException(this.message);
  @override
  String toString() => message;
}

class ConnectionException extends FtpClientException {
  ConnectionException(super.message);
}

class AuthenticationException extends FtpClientException {
  AuthenticationException(super.message);
}

class NotFoundException extends FtpClientException {
  NotFoundException(super.message);
}

class ServerException extends FtpClientException {
  ServerException(super.message);
}

class TimeoutException extends FtpClientException {
  TimeoutException(super.message);
}
```

### HTML Parsing

**Python Implementation:** `parse_html()` in `ftp_client.py`

```python
def parse_html(base_url: str, response_html: bytes) -> Tuple[List[Folder], List[File]]:
    soup = BeautifulSoup(response_html, 'html.parser')
    td_tags = soup.find_all('td', class_='fb-n')
    folders: List[Folder] = []
    files: List[File] = []

    # Add parent directory
    folders.append(Folder(name="..", url=urljoin(base_url, "..")))

    for td_tag in td_tags:
        a_tags = td_tag.find_all('a')
        for a_tag in a_tags:
            value = a_tag.text
            href = a_tag['href']

            if href.startswith('..'):
                continue

            absolute_url = urljoin(base_url, href)

            if href.endswith('/'):
                folders.append(Folder(name=value, url=absolute_url))
            else:
                files.append(File(name=value, url=absolute_url))

    return folders, files
```

**Flutter Equivalent:**

```dart
import 'package:html/parser.dart' as html_parser;
import 'package:html/dom.dart';

class HtmlParser {
  static Future<DirectoryListing> parseHtml({
    required String baseUrl,
    required String htmlContent,
  }) async {
    final document = html_parser.parse(htmlContent);
    final tdTags = document.querySelectorAll('td.fb-n');

    final folders = <Folder>[];
    final files = <FileItem>[];

    // Add parent directory
    final parentUrl = Uri.parse(baseUrl).resolve('..').toString();
    folders.add(Folder(name: '..', url: parentUrl));

    for (var tdTag in tdTags) {
      final aTags = tdTag.querySelectorAll('a');

      for (var aTag in aTags) {
        final name = aTag.text;
        final href = aTag.attributes['href'] ?? '';

        if (href.startsWith('..')) continue;

        final absoluteUrl = Uri.parse(baseUrl).resolve(href).toString();

        if (href.endsWith('/')) {
          folders.add(Folder(name: name, url: absoluteUrl));
        } else {
          files.add(FileItem(name: name, url: absoluteUrl));
        }
      }
    }

    return DirectoryListing(folders: folders, files: files);
  }
}

class DirectoryListing {
  final List<Folder> folders;
  final List<FileItem> files;

  DirectoryListing({
    required this.folders,
    required this.files,
  });

  List<dynamic> get allItems => [...folders, ...files];
}
```

### Download Manager

**Python Implementation:** `download_file_async()` in `ftp_client.py`

```dart
class DownloadManager {
  final Dio _dio;
  final String downloadDirectory;

  DownloadManager({
    required this.downloadDirectory,
  }) : _dio = Dio();

  Future<bool> downloadFile({
    required FileItem file,
    required Function(double progress) onProgress,
    String? basicAuthHeader,
    CancelToken? cancelToken,
  }) async {
    try {
      final filePath = '$downloadDirectory/${file.name}';

      await _dio.download(
        file.url,
        filePath,
        options: Options(
          headers: basicAuthHeader != null
            ? {'Authorization': basicAuthHeader}
            : null,
        ),
        onReceiveProgress: (received, total) {
          if (total != -1) {
            final progress = received / total;
            onProgress(progress);
          }
        },
        cancelToken: cancelToken,
      );

      return true;
    } on DioException catch (e) {
      print('Download error: $e');
      return false;
    }
  }

  Future<List<bool>> downloadFiles({
    required List<FileItem> files,
    required Function(int index, double progress) onProgress,
    String? basicAuthHeader,
  }) async {
    final results = <bool>[];

    for (var i = 0; i < files.length; i++) {
      final result = await downloadFile(
        file: files[i],
        onProgress: (progress) => onProgress(i, progress),
        basicAuthHeader: basicAuthHeader,
      );
      results.add(result);
    }

    return results;
  }
}
```

---

## 6. State Management

### Recommended: BLoC Pattern

**Why BLoC?**
- Clear separation of business logic and UI
- Testable
- Reactive streams
- Built-in error handling
- Works well with async operations

### File Browser BLoC Example

```dart
// Events
abstract class FileBrowserEvent extends Equatable {
  const FileBrowserEvent();

  @override
  List<Object?> get props => [];
}

class LoadDirectory extends FileBrowserEvent {
  final String url;
  final bool forceRefresh;

  const LoadDirectory(this.url, {this.forceRefresh = false});

  @override
  List<Object?> get props => [url, forceRefresh];
}

class NavigateToFolder extends FileBrowserEvent {
  final Folder folder;

  const NavigateToFolder(this.folder);

  @override
  List<Object?> get props => [folder];
}

class NavigateBack extends FileBrowserEvent {}

class ToggleFileSelection extends FileBrowserEvent {
  final int index;

  const ToggleFileSelection(this.index);

  @override
  List<Object?> get props => [index];
}

class ClearSelection extends FileBrowserEvent {}

// States
abstract class FileBrowserState extends Equatable {
  const FileBrowserState();

  @override
  List<Object?> get props => [];
}

class FileBrowserInitial extends FileBrowserState {}

class FileBrowserLoading extends FileBrowserState {}

class FileBrowserLoaded extends FileBrowserState {
  final DirectoryListing listing;
  final String currentUrl;
  final List<String> navigationHistory;
  final Set<int> selectedIndices;

  const FileBrowserLoaded({
    required this.listing,
    required this.currentUrl,
    required this.navigationHistory,
    this.selectedIndices = const {},
  });

  @override
  List<Object?> get props => [listing, currentUrl, navigationHistory, selectedIndices];

  FileBrowserLoaded copyWith({
    DirectoryListing? listing,
    String? currentUrl,
    List<String>? navigationHistory,
    Set<int>? selectedIndices,
  }) {
    return FileBrowserLoaded(
      listing: listing ?? this.listing,
      currentUrl: currentUrl ?? this.currentUrl,
      navigationHistory: navigationHistory ?? this.navigationHistory,
      selectedIndices: selectedIndices ?? this.selectedIndices,
    );
  }
}

class FileBrowserError extends FileBrowserState {
  final String message;

  const FileBrowserError(this.message);

  @override
  List<Object?> get props => [message];
}

// BLoC
class FileBrowserBloc extends Bloc<FileBrowserEvent, FileBrowserState> {
  final FtpRepository repository;
  final CacheManager cacheManager;

  FileBrowserBloc({
    required this.repository,
    required this.cacheManager,
  }) : super(FileBrowserInitial()) {
    on<LoadDirectory>(_onLoadDirectory);
    on<NavigateToFolder>(_onNavigateToFolder);
    on<NavigateBack>(_onNavigateBack);
    on<ToggleFileSelection>(_onToggleFileSelection);
    on<ClearSelection>(_onClearSelection);
  }

  Future<void> _onLoadDirectory(
    LoadDirectory event,
    Emitter<FileBrowserState> emit,
  ) async {
    emit(FileBrowserLoading());

    try {
      DirectoryListing listing;

      // Try cache first
      if (!event.forceRefresh) {
        final cached = await cacheManager.getCachedListing(event.url);
        if (cached != null) {
          listing = cached;
        } else {
          listing = await repository.fetchDirectory(event.url);
          await cacheManager.cacheListing(event.url, listing);
        }
      } else {
        listing = await repository.fetchDirectory(event.url);
        await cacheManager.cacheListing(event.url, listing);
      }

      final currentState = state;
      final history = currentState is FileBrowserLoaded
          ? currentState.navigationHistory
          : <String>[];

      emit(FileBrowserLoaded(
        listing: listing,
        currentUrl: event.url,
        navigationHistory: history,
      ));
    } on FtpClientException catch (e) {
      emit(FileBrowserError(e.message));
    } catch (e) {
      emit(FileBrowserError('Unexpected error: $e'));
    }
  }

  Future<void> _onNavigateToFolder(
    NavigateToFolder event,
    Emitter<FileBrowserState> emit,
  ) async {
    final currentState = state;
    if (currentState is! FileBrowserLoaded) return;

    final newHistory = [...currentState.navigationHistory, currentState.currentUrl];

    add(LoadDirectory(event.folder.url));
  }

  Future<void> _onNavigateBack(
    NavigateBack event,
    Emitter<FileBrowserState> emit,
  ) async {
    final currentState = state;
    if (currentState is! FileBrowserLoaded) return;

    if (currentState.navigationHistory.isEmpty) return;

    final newHistory = [...currentState.navigationHistory];
    final previousUrl = newHistory.removeLast();

    add(LoadDirectory(previousUrl));
  }

  Future<void> _onToggleFileSelection(
    ToggleFileSelection event,
    Emitter<FileBrowserState> emit,
  ) async {
    final currentState = state;
    if (currentState is! FileBrowserLoaded) return;

    final newSelection = Set<int>.from(currentState.selectedIndices);
    if (newSelection.contains(event.index)) {
      newSelection.remove(event.index);
    } else {
      newSelection.add(event.index);
    }

    emit(currentState.copyWith(selectedIndices: newSelection));
  }

  Future<void> _onClearSelection(
    ClearSelection event,
    Emitter<FileBrowserState> emit,
  ) async {
    final currentState = state;
    if (currentState is! FileBrowserLoaded) return;

    emit(currentState.copyWith(selectedIndices: {}));
  }
}
```

---

## 7. UI/UX Design

### Screen Hierarchy

```
1. Splash Screen
2. Server Selection Screen
   ├─> Add/Edit Server Screen
   └─> Server Settings Screen
3. File Browser Screen (Main)
   ├─> Search Screen
   ├─> Bookmarks Screen
   ├─> Batch Selection Mode
   └─> Settings Screen
4. Media Player Screen
   ├─> Video Player
   ├─> Audio Player
   └─> Image Viewer
5. Download Manager Screen
6. Settings Screen
```

### File Browser Screen (Main Screen)

**Layout Components:**

1. **App Bar**
   - Server name
   - Settings icon
   - Search icon
   - Bookmark icon

2. **Breadcrumb Navigation**
   - Horizontal scrollable path
   - Tap to jump to parent folders
   - Server name > Folder1 > Folder2 > ...

3. **Directory Listing**
   - List/Grid view toggle
   - File/folder icons with type indicators
   - File size (if available)
   - Checkbox for selection mode
   - Pull-to-refresh
   - Infinite scroll (if needed)

4. **Bottom Navigation/Action Bar**
   - Home
   - Bookmarks
   - Downloads
   - Settings

5. **Floating Action Button (FAB)**
   - Context-aware actions:
     - Play all media
     - Download all
     - Multi-select mode

**File/Folder Item Design:**

```dart
class FileListTile extends StatelessWidget {
  final dynamic item; // Folder or FileItem
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    final isFolder = item is Folder;

    return ListTile(
      leading: isSelected
          ? const Icon(Icons.check_circle, color: Colors.green)
          : _getIcon(),
      title: Text(
        item.name,
        style: TextStyle(
          fontWeight: isFolder ? FontWeight.bold : FontWeight.normal,
          color: isFolder ? Colors.blue : Colors.black87,
        ),
      ),
      subtitle: !isFolder && item.sizeBytes != null
          ? Text(item.formattedSize)
          : null,
      trailing: !isFolder ? _getTrailingIcon() : null,
      onTap: onTap,
      onLongPress: onLongPress,
    );
  }

  Widget _getIcon() {
    if (item is Folder) {
      return item.isParentDirectory
          ? const Icon(Icons.arrow_upward, color: Colors.red)
          : const Icon(Icons.folder, color: Colors.amber);
    }

    switch (item.fileType) {
      case FileType.video:
        return const Icon(Icons.play_circle_filled, color: Colors.blue);
      case FileType.audio:
        return const Icon(Icons.music_note, color: Colors.purple);
      case FileType.image:
        return const Icon(Icons.image, color: Colors.green);
      default:
        return const Icon(Icons.insert_drive_file, color: Colors.grey);
    }
  }

  Widget? _getTrailingIcon() {
    return PopupMenuButton<String>(
      onSelected: (value) {
        // Handle actions: download, share, etc.
      },
      itemBuilder: (context) => [
        const PopupMenuItem(value: 'download', child: Text('Download')),
        const PopupMenuItem(value: 'share', child: Text('Share')),
        if (item.fileType != FileType.other)
          const PopupMenuItem(value: 'play', child: Text('Play')),
      ],
    );
  }
}
```

### Color Scheme & Theming

**Recommended Palette:**

```dart
class AppColors {
  // Primary colors
  static const primary = Color(0xFF2196F3);
  static const primaryDark = Color(0xFF1976D2);
  static const accent = Color(0xFF00BCD4);

  // File type colors
  static const folderColor = Color(0xFFFFA726);
  static const videoColor = Color(0xFF2196F3);
  static const audioColor = Color(0xFF9C27B0);
  static const imageColor = Color(0xFF4CAF50);
  static const fileColor = Color(0xFF757575);

  // Status colors
  static const success = Color(0xFF4CAF50);
  static const error = Color(0xFFD32F2F);
  static const warning = Color(0xFFFF9800);
  static const info = Color(0xFF2196F3);

  // Background
  static const background = Color(0xFFF5F5F5);
  static const surface = Colors.white;
}
```

### Key UI Interactions

1. **Navigation**
   - Tap folder → Navigate into folder
   - Tap parent (..) → Go back one level
   - Hardware back button → Navigate back
   - Swipe from left edge → Navigate back (iOS/Android)

2. **File Selection**
   - Long press → Enter multi-select mode
   - Tap in multi-select → Toggle selection
   - FAB in multi-select → Show batch actions

3. **Media Playback**
   - Tap media file → Play immediately
   - Play all → Create playlist from all media in folder

4. **Downloads**
   - Tap download → Show location picker
   - Download all → Batch download with progress

5. **Bookmarks**
   - Add bookmark → Show name input dialog
   - View bookmarks → Show list with server grouping
   - Navigate to bookmark → Jump to URL

---

## 8. Caching System

### Python Implementation (cache.py)

**Features:**
- TTL-based expiration (5 minutes default)
- Two-tier caching (memory + disk)
- Hash-based cache keys (SHA256 of URL)
- JSON file storage
- Automatic cleanup of expired entries

**Flutter Implementation:**

```dart
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:path_provider/path_provider.dart';

class CacheManager {
  final Duration ttl;
  final Map<String, CacheEntry> _memoryCache = {};
  late final String _cacheFilePath;

  CacheManager({
    this.ttl = const Duration(minutes: 5),
  });

  Future<void> init() async {
    final cacheDir = await getApplicationCacheDirectory();
    final samfptDir = Directory('${cacheDir.path}/samftp_cache');
    if (!await samfptDir.exists()) {
      await samfptDir.create(recursive: true);
    }
    _cacheFilePath = '${samfptDir.path}/directory_cache.json';
  }

  String _urlToHash(String url) {
    final bytes = utf8.encode(url);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  Future<DirectoryListing?> getCachedListing(String url) async {
    final urlHash = _urlToHash(url);

    // Check memory cache first
    if (_memoryCache.containsKey(urlHash)) {
      final entry = _memoryCache[urlHash]!;
      if (!entry.isExpired(ttl)) {
        return DirectoryListing(
          folders: entry.folders,
          files: entry.files,
        );
      } else {
        _memoryCache.remove(urlHash);
      }
    }

    // Check disk cache
    final cacheData = await _loadCacheFromDisk();
    if (cacheData.containsKey(urlHash)) {
      final entryJson = cacheData[urlHash];
      final entry = CacheEntry.fromJson(entryJson);

      if (!entry.isExpired(ttl)) {
        _memoryCache[urlHash] = entry;
        return DirectoryListing(
          folders: entry.folders,
          files: entry.files,
        );
      } else {
        cacheData.remove(urlHash);
        await _saveCacheToDisk(cacheData);
      }
    }

    return null;
  }

  Future<void> cacheListing(String url, DirectoryListing listing) async {
    final urlHash = _urlToHash(url);
    final entry = CacheEntry(
      url: url,
      timestamp: DateTime.now(),
      folders: listing.folders,
      files: listing.files,
    );

    // Update memory cache
    _memoryCache[urlHash] = entry;

    // Update disk cache
    final cacheData = await _loadCacheFromDisk();
    cacheData[urlHash] = entry.toJson();
    await _saveCacheToDisk(cacheData);
  }

  Future<void> invalidateCache(String url) async {
    final urlHash = _urlToHash(url);

    // Remove from memory
    _memoryCache.remove(urlHash);

    // Remove from disk
    final cacheData = await _loadCacheFromDisk();
    cacheData.remove(urlHash);
    await _saveCacheToDisk(cacheData);
  }

  Future<void> clearAllCache() async {
    _memoryCache.clear();

    final file = File(_cacheFilePath);
    if (await file.exists()) {
      await file.delete();
    }
  }

  Future<Map<String, dynamic>> getCacheStats() async {
    final cacheData = await _loadCacheFromDisk();
    final totalEntries = cacheData.length;

    int expiredEntries = 0;
    for (var entryJson in cacheData.values) {
      final entry = CacheEntry.fromJson(entryJson);
      if (entry.isExpired(ttl)) {
        expiredEntries++;
      }
    }

    final validEntries = totalEntries - expiredEntries;

    final file = File(_cacheFilePath);
    final cacheSize = await file.exists() ? await file.length() : 0;

    return {
      'total_entries': totalEntries,
      'valid_entries': validEntries,
      'expired_entries': expiredEntries,
      'cache_size_bytes': cacheSize,
      'cache_size_kb': cacheSize / 1024,
      'cache_location': _cacheFilePath,
      'ttl_seconds': ttl.inSeconds,
    };
  }

  Future<int> cleanupExpired() async {
    final cacheData = await _loadCacheFromDisk();
    final originalSize = cacheData.length;

    cacheData.removeWhere((key, value) {
      final entry = CacheEntry.fromJson(value);
      return entry.isExpired(ttl);
    });

    final removedCount = originalSize - cacheData.length;
    if (removedCount > 0) {
      await _saveCacheToDisk(cacheData);
    }

    return removedCount;
  }

  Future<Map<String, dynamic>> _loadCacheFromDisk() async {
    final file = File(_cacheFilePath);
    if (!await file.exists()) {
      return {};
    }

    try {
      final contents = await file.readAsString();
      return json.decode(contents) as Map<String, dynamic>;
    } catch (e) {
      print('Error loading cache: $e');
      return {};
    }
  }

  Future<void> _saveCacheToDisk(Map<String, dynamic> cacheData) async {
    final file = File(_cacheFilePath);
    try {
      await file.writeAsString(json.encode(cacheData));
    } catch (e) {
      print('Error saving cache: $e');
    }
  }
}
```

---

## 9. Bookmarks System

### Python Implementation (bookmarks.py)

**Features:**
- CRUD operations (Create, Read, Update, Delete)
- JSON file storage
- Server grouping
- Import/export functionality
- Duplicate detection
- Timestamp tracking

**Flutter Implementation:**

```dart
import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class BookmarkManager {
  late final String _bookmarksFilePath;
  List<Bookmark>? _bookmarksCache;

  Future<void> init() async {
    final appDir = await getApplicationDocumentsDirectory();
    final configDir = Directory('${appDir.path}/samftp_config');
    if (!await configDir.exists()) {
      await configDir.create(recursive: true);
    }
    _bookmarksFilePath = '${configDir.path}/bookmarks.json';
  }

  Future<List<Bookmark>> _loadBookmarks() async {
    if (_bookmarksCache != null) {
      return _bookmarksCache!;
    }

    final file = File(_bookmarksFilePath);
    if (!await file.exists()) {
      _bookmarksCache = [];
      return _bookmarksCache!;
    }

    try {
      final contents = await file.readAsString();
      final jsonList = json.decode(contents) as List;
      _bookmarksCache = jsonList
          .map((item) => Bookmark.fromJson(item as Map<String, dynamic>))
          .toList();
      return _bookmarksCache!;
    } catch (e) {
      print('Error loading bookmarks: $e');
      _bookmarksCache = [];
      return _bookmarksCache!;
    }
  }

  Future<void> _saveBookmarks(List<Bookmark> bookmarks) async {
    final file = File(_bookmarksFilePath);
    try {
      final jsonList = bookmarks.map((b) => b.toJson()).toList();
      await file.writeAsString(json.encode(jsonList));
      _bookmarksCache = bookmarks;
    } catch (e) {
      print('Error saving bookmarks: $e');
    }
  }

  Future<bool> addBookmark({
    required String name,
    required String server,
    required String url,
  }) async {
    final bookmarks = await _loadBookmarks();

    // Check if name already exists
    if (bookmarks.any((b) => b.name.toLowerCase() == name.toLowerCase())) {
      return false;
    }

    final bookmark = Bookmark(
      name: name,
      server: server,
      url: url,
      timestamp: DateTime.now(),
    );

    bookmarks.add(bookmark);
    await _saveBookmarks(bookmarks);
    return true;
  }

  Future<bool> removeBookmark(String name) async {
    final bookmarks = await _loadBookmarks();
    final originalLength = bookmarks.length;

    bookmarks.removeWhere(
      (b) => b.name.toLowerCase() == name.toLowerCase(),
    );

    if (bookmarks.length < originalLength) {
      await _saveBookmarks(bookmarks);
      return true;
    }

    return false;
  }

  Future<Bookmark?> getBookmark(String name) async {
    final bookmarks = await _loadBookmarks();
    try {
      return bookmarks.firstWhere(
        (b) => b.name.toLowerCase() == name.toLowerCase(),
      );
    } catch (e) {
      return null;
    }
  }

  Future<List<Bookmark>> listBookmarks() async {
    final bookmarks = await _loadBookmarks();
    bookmarks.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return bookmarks;
  }

  Future<String?> isBookmarked(String url) async {
    final bookmarks = await _loadBookmarks();
    try {
      final bookmark = bookmarks.firstWhere((b) => b.url == url);
      return bookmark.name;
    } catch (e) {
      return null;
    }
  }

  Future<bool> updateBookmark({
    required String name,
    String? newName,
    String? newUrl,
  }) async {
    final bookmarks = await _loadBookmarks();

    try {
      final index = bookmarks.indexWhere(
        (b) => b.name.toLowerCase() == name.toLowerCase(),
      );

      if (index == -1) return false;

      // Check if new name already exists
      if (newName != null &&
          bookmarks.any((b) =>
              b.name.toLowerCase() == newName.toLowerCase() &&
              b.name != bookmarks[index].name)) {
        return false;
      }

      final updatedBookmark = Bookmark(
        name: newName ?? bookmarks[index].name,
        server: bookmarks[index].server,
        url: newUrl ?? bookmarks[index].url,
        timestamp: DateTime.now(),
      );

      bookmarks[index] = updatedBookmark;
      await _saveBookmarks(bookmarks);
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<List<Bookmark>> getBookmarksByServer(String server) async {
    final bookmarks = await _loadBookmarks();
    return bookmarks.where((b) => b.server == server).toList();
  }

  Future<int> clearAllBookmarks() async {
    final bookmarks = await _loadBookmarks();
    final count = bookmarks.length;

    if (count > 0) {
      await _saveBookmarks([]);
    }

    return count;
  }

  Future<bool> exportBookmarks(String filePath) async {
    final bookmarks = await _loadBookmarks();

    try {
      final jsonList = bookmarks.map((b) => b.toJson()).toList();
      final file = File(filePath);
      await file.writeAsString(json.encode(jsonList));
      return true;
    } catch (e) {
      print('Error exporting bookmarks: $e');
      return false;
    }
  }

  Future<int> importBookmarks(String filePath, {bool merge = true}) async {
    try {
      final file = File(filePath);
      final contents = await file.readAsString();
      final jsonList = json.decode(contents) as List;

      final imported = jsonList
          .map((item) => Bookmark.fromJson(item as Map<String, dynamic>))
          .toList();

      if (merge) {
        final existing = await _loadBookmarks();
        final existingNames = existing.map((b) => b.name.toLowerCase()).toSet();

        final newBookmarks = imported
            .where((b) => !existingNames.contains(b.name.toLowerCase()))
            .toList();

        final allBookmarks = [...existing, ...newBookmarks];
        await _saveBookmarks(allBookmarks);
        return newBookmarks.length;
      } else {
        await _saveBookmarks(imported);
        return imported.length;
      }
    } catch (e) {
      print('Error importing bookmarks: $e');
      return 0;
    }
  }
}
```

---

## 10. Media Player Integration

### Python Implementation (player.py)

**Features:**
- Multi-player support (mpv, VLC, IINA)
- Player preference hierarchy (override > session > saved > prompt)
- Background playback
- Playlist support (M3U for mpv, URLs for VLC/IINA)
- File type detection

### Flutter Implementation

**Video Player:**

```dart
import 'package:video_player/video_player.dart';
import 'package:chewie/chewie.dart';

class VideoPlayerScreen extends StatefulWidget {
  final FileItem file;
  final List<FileItem>? playlist;

  const VideoPlayerScreen({
    required this.file,
    this.playlist,
  });

  @override
  State<VideoPlayerScreen> createState() => _VideoPlayerScreenState();
}

class _VideoPlayerScreenState extends State<VideoPlayerScreen> {
  late VideoPlayerController _videoController;
  ChewieController? _chewieController;
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    _initializePlayer();
  }

  Future<void> _initializePlayer() async {
    final files = widget.playlist ?? [widget.file];
    final currentFile = files[_currentIndex];

    _videoController = VideoPlayerController.networkUrl(
      Uri.parse(currentFile.url),
    );

    await _videoController.initialize();

    _chewieController = ChewieController(
      videoPlayerController: _videoController,
      autoPlay: true,
      looping: false,
      allowFullScreen: true,
      allowPlaybackSpeedChanging: true,
      additionalOptions: (context) {
        return [
          OptionItem(
            onTap: _playNext,
            iconData: Icons.skip_next,
            title: 'Next',
          ),
          OptionItem(
            onTap: _playPrevious,
            iconData: Icons.skip_previous,
            title: 'Previous',
          ),
        ];
      },
    );

    setState(() {});

    _videoController.addListener(() {
      if (_videoController.value.position ==
          _videoController.value.duration) {
        _playNext();
      }
    });
  }

  void _playNext() {
    final files = widget.playlist ?? [widget.file];
    if (_currentIndex < files.length - 1) {
      _currentIndex++;
      _disposeControllers();
      _initializePlayer();
    }
  }

  void _playPrevious() {
    if (_currentIndex > 0) {
      _currentIndex--;
      _disposeControllers();
      _initializePlayer();
    }
  }

  void _disposeControllers() {
    _chewieController?.dispose();
    _videoController.dispose();
  }

  @override
  void dispose() {
    _disposeControllers();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.file.name),
      ),
      body: _chewieController != null
          ? Chewie(controller: _chewieController!)
          : const Center(child: CircularProgressIndicator()),
    );
  }
}
```

**Audio Player:**

```dart
import 'package:just_audio/just_audio.dart';
import 'package:audio_video_progress_bar/audio_video_progress_bar.dart';

class AudioPlayerScreen extends StatefulWidget {
  final FileItem file;
  final List<FileItem>? playlist;

  const AudioPlayerScreen({
    required this.file,
    this.playlist,
  });

  @override
  State<AudioPlayerScreen> createState() => _AudioPlayerScreenState();
}

class _AudioPlayerScreenState extends State<AudioPlayerScreen> {
  late AudioPlayer _audioPlayer;

  @override
  void initState() {
    super.initState();
    _audioPlayer = AudioPlayer();
    _setupPlaylist();
  }

  Future<void> _setupPlaylist() async {
    final files = widget.playlist ?? [widget.file];
    final playlist = ConcatenatingAudioSource(
      children: files
          .map((f) => AudioSource.uri(Uri.parse(f.url)))
          .toList(),
    );

    await _audioPlayer.setAudioSource(playlist);
    _audioPlayer.play();
  }

  @override
  void dispose() {
    _audioPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.file.name),
      ),
      body: StreamBuilder<PlayerState>(
        stream: _audioPlayer.playerStateStream,
        builder: (context, snapshot) {
          final playerState = snapshot.data;
          final processingState = playerState?.processingState;
          final playing = playerState?.playing;

          return Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Album art placeholder
              Container(
                width: 200,
                height: 200,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.music_note, size: 80),
              ),

              const SizedBox(height: 32),

              // Progress bar
              StreamBuilder<Duration?>(
                stream: _audioPlayer.positionStream,
                builder: (context, snapshot) {
                  final position = snapshot.data ?? Duration.zero;
                  final duration = _audioPlayer.duration ?? Duration.zero;

                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: ProgressBar(
                      progress: position,
                      total: duration,
                      onSeek: _audioPlayer.seek,
                    ),
                  );
                },
              ),

              const SizedBox(height: 32),

              // Controls
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.skip_previous),
                    iconSize: 48,
                    onPressed: _audioPlayer.hasPrevious
                        ? _audioPlayer.seekToPrevious
                        : null,
                  ),
                  IconButton(
                    icon: Icon(
                      playing == true ? Icons.pause : Icons.play_arrow,
                    ),
                    iconSize: 64,
                    onPressed: () {
                      if (playing == true) {
                        _audioPlayer.pause();
                      } else {
                        _audioPlayer.play();
                      }
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.skip_next),
                    iconSize: 48,
                    onPressed: _audioPlayer.hasNext
                        ? _audioPlayer.seekToNext
                        : null,
                  ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}
```

**Image Viewer:**

```dart
import 'package:photo_view/photo_view.dart';
import 'package:photo_view/photo_view_gallery.dart';

class ImageViewerScreen extends StatefulWidget {
  final FileItem file;
  final List<FileItem>? images;

  const ImageViewerScreen({
    required this.file,
    this.images,
  });

  @override
  State<ImageViewerScreen> createState() => _ImageViewerScreenState();
}

class _ImageViewerScreenState extends State<ImageViewerScreen> {
  late PageController _pageController;
  late int _currentIndex;

  @override
  void initState() {
    super.initState();
    final images = widget.images ?? [widget.file];
    _currentIndex = images.indexWhere((img) => img.url == widget.file.url);
    _pageController = PageController(initialPage: _currentIndex);
  }

  @override
  Widget build(BuildContext context) {
    final images = widget.images ?? [widget.file];

    return Scaffold(
      appBar: AppBar(
        title: Text('${_currentIndex + 1} / ${images.length}'),
        backgroundColor: Colors.black,
      ),
      body: PhotoViewGallery.builder(
        pageController: _pageController,
        itemCount: images.length,
        builder: (context, index) {
          return PhotoViewGalleryPageOptions(
            imageProvider: NetworkImage(images[index].url),
            minScale: PhotoViewComputedScale.contained,
            maxScale: PhotoViewComputedScale.covered * 2,
          );
        },
        onPageChanged: (index) {
          setState(() => _currentIndex = index);
        },
        backgroundDecoration: const BoxDecoration(
          color: Colors.black,
        ),
      ),
    );
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }
}
```

---

## 11. Configuration Management

### Python Implementation (config.py)

**Features:**
- `.env` file storage in user home directory
- Interactive configuration wizard
- Server validation and connection testing
- First-run detection
- Default player/download directory

### Flutter Implementation

```dart
import 'dart:convert';
import 'dart:io';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ConfigManager {
  static const _secureStorage = FlutterSecureStorage();
  late final String _configFilePath;

  Future<void> init() async {
    final appDir = await getApplicationDocumentsDirectory();
    _configFilePath = '${appDir.path}/config.json';
  }

  // Server management
  Future<List<Server>> loadServers() async {
    final file = File(_configFilePath);
    if (!await file.exists()) {
      return [];
    }

    try {
      final contents = await file.readAsString();
      final json = jsonDecode(contents) as Map<String, dynamic>;
      final serversJson = json['servers'] as List? ?? [];

      final servers = <Server>[];
      for (var serverJson in serversJson) {
        final server = Server.fromJson(serverJson);
        // Load password from secure storage
        if (server.username != null) {
          final password = await _secureStorage.read(
            key: 'server_${server.name}_password',
          );
          servers.add(Server(
            name: server.name,
            url: server.url,
            username: server.username,
            password: password,
            lastAccessed: server.lastAccessed,
            preferredPlayer: server.preferredPlayer,
          ));
        } else {
          servers.add(server);
        }
      }

      return servers;
    } catch (e) {
      print('Error loading servers: $e');
      return [];
    }
  }

  Future<bool> saveServers(List<Server> servers) async {
    try {
      // Save passwords to secure storage
      for (var server in servers) {
        if (server.password != null) {
          await _secureStorage.write(
            key: 'server_${server.name}_password',
            value: server.password,
          );
        }
      }

      // Save server config (without passwords)
      final serversJson = servers.map((s) {
        return Server(
          name: s.name,
          url: s.url,
          username: s.username,
          // Don't include password in JSON
          lastAccessed: s.lastAccessed,
          preferredPlayer: s.preferredPlayer,
        ).toJson();
      }).toList();

      final config = {
        'servers': serversJson,
      };

      final file = File(_configFilePath);
      await file.writeAsString(jsonEncode(config));
      return true;
    } catch (e) {
      print('Error saving servers: $e');
      return false;
    }
  }

  Future<bool> addServer(Server server) async {
    final servers = await loadServers();
    servers.add(server);
    return await saveServers(servers);
  }

  Future<bool> removeServer(String serverName) async {
    final servers = await loadServers();
    servers.removeWhere((s) => s.name == serverName);

    // Remove password from secure storage
    await _secureStorage.delete(key: 'server_${serverName}_password');

    return await saveServers(servers);
  }

  Future<bool> updateServer(Server server) async {
    final servers = await loadServers();
    final index = servers.indexWhere((s) => s.name == server.name);

    if (index == -1) return false;

    servers[index] = server;
    return await saveServers(servers);
  }

  // Test server connection
  Future<(bool, String?)> testServerConnection(Server server) async {
    try {
      final dio = Dio();
      final response = await dio.get(
        server.url,
        options: Options(
          headers: server.basicAuthHeader != null
              ? {'Authorization': server.basicAuthHeader}
              : null,
          validateStatus: (status) => status != null && status < 500,
        ),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 401) {
        return (false, 'Authentication required - invalid or missing credentials');
      } else if (response.statusCode == 403) {
        return (false, 'Access forbidden - check permissions');
      } else if (response.statusCode == 404) {
        return (false, 'Server not found - check URL');
      } else if (response.statusCode! >= 400) {
        return (false, 'Server error (HTTP ${response.statusCode})');
      }

      return (true, null);
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout) {
        return (false, 'Connection timeout');
      } else if (e.type == DioExceptionType.connectionError) {
        return (false, 'Connection failed - check network and server address');
      }
      return (false, 'Request error: ${e.message}');
    } catch (e) {
      return (false, 'Unexpected error: $e');
    }
  }

  // Preferences
  Future<String?> getDefaultPlayer() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('default_player');
  }

  Future<bool> setDefaultPlayer(String player) async {
    final prefs = await SharedPreferences.getInstance();
    return await prefs.setString('default_player', player);
  }

  Future<String?> getDefaultDownloadDirectory() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('default_download_dir');
  }

  Future<bool> setDefaultDownloadDirectory(String directory) async {
    final prefs = await SharedPreferences.getInstance();
    return await prefs.setString('default_download_dir', directory);
  }

  // First run detection
  Future<bool> isFirstRun() async {
    final prefs = await SharedPreferences.getInstance();
    final hasRun = prefs.getBool('has_run') ?? false;

    if (!hasRun) {
      await prefs.setBool('has_run', true);
      return true;
    }

    return false;
  }
}
```

---

## 12. Error Handling & Logging

### Python Implementation (main.py)

**Features:**
- Centralized error logging to file
- Platform-specific log directories (using `platformdirs`)
- Timestamp and context tracking
- Full traceback capture

### Flutter Implementation

```dart
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:intl/intl.dart';
import 'package:logger/logger.dart';

class AppLogger {
  static final AppLogger _instance = AppLogger._internal();
  factory AppLogger() => _instance;

  late final Logger _logger;
  late final File _logFile;

  AppLogger._internal();

  Future<void> init() async {
    final appDir = await getApplicationDocumentsDirectory();
    final logDir = Directory('${appDir.path}/logs');
    if (!await logDir.exists()) {
      await logDir.create(recursive: true);
    }

    _logFile = File('${logDir.path}/app.log');

    _logger = Logger(
      printer: PrettyPrinter(
        methodCount: 2,
        errorMethodCount: 8,
        lineLength: 120,
        colors: true,
        printEmojis: true,
        printTime: true,
      ),
      output: MultiOutput([
        ConsoleOutput(),
        FileOutput(file: _logFile),
      ]),
    );
  }

  void logError(
    dynamic error, {
    StackTrace? stackTrace,
    String? context,
  }) {
    final timestamp = DateFormat('yyyy-MM-dd HH:mm:ss').format(DateTime.now());
    final message = [
      '=' * 80,
      'Timestamp: $timestamp',
      if (context != null) 'Context: $context',
      'Error Type: ${error.runtimeType}',
      'Error Message: $error',
      if (stackTrace != null) '\nStack Trace:\n$stackTrace',
      '=' * 80,
    ].join('\n');

    _logger.e(message);
  }

  void logInfo(String message, {String? context}) {
    _logger.i(context != null ? '[$context] $message' : message);
  }

  void logWarning(String message, {String? context}) {
    _logger.w(context != null ? '[$context] $message' : message);
  }

  void logDebug(String message, {String? context}) {
    _logger.d(context != null ? '[$context] $message' : message);
  }

  Future<String> getLogFilePath() async {
    return _logFile.path;
  }

  Future<String> getLogContents() async {
    if (await _logFile.exists()) {
      return await _logFile.readAsString();
    }
    return '';
  }

  Future<void> clearLogs() async {
    if (await _logFile.exists()) {
      await _logFile.delete();
    }
  }
}

class FileOutput extends LogOutput {
  final File file;

  FileOutput({required this.file});

  @override
  void output(OutputEvent event) {
    for (var line in event.lines) {
      file.writeAsStringSync('$line\n', mode: FileMode.append);
    }
  }
}
```

**Global Error Handler:**

```dart
void main() {
  // Catch Flutter framework errors
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    AppLogger().logError(
      details.exception,
      stackTrace: details.stack,
      context: 'Flutter Framework Error',
    );
  };

  // Catch async errors
  PlatformDispatcher.instance.onError = (error, stack) {
    AppLogger().logError(
      error,
      stackTrace: stack,
      context: 'Async Error',
    );
    return true;
  };

  runApp(const MyApp());
}
```

---

## 13. Flutter Packages Recommendations

### Core Packages

```yaml
dependencies:
  flutter:
    sdk: flutter

  # State Management
  flutter_bloc: ^8.1.3
  equatable: ^2.0.5
  # OR
  riverpod: ^2.4.0
  flutter_riverpod: ^2.4.0

  # Networking
  dio: ^5.3.3
  html: ^0.15.4
  connectivity_plus: ^5.0.1

  # Storage
  shared_preferences: ^2.2.2
  flutter_secure_storage: ^9.0.0
  path_provider: ^2.1.1
  hive: ^2.2.3
  hive_flutter: ^1.1.0

  # UI Components
  cached_network_image: ^3.3.0
  flutter_svg: ^2.0.9
  shimmer: ^3.0.0
  pull_to_refresh: ^2.0.0
  flutter_slidable: ^3.0.0

  # Media Players
  video_player: ^2.8.1
  chewie: ^1.7.1
  just_audio: ^0.9.36
  audio_video_progress_bar: ^1.0.1
  photo_view: ^0.14.0

  # File Operations
  file_picker: ^6.1.1
  permission_handler: ^11.0.1
  open_filex: ^4.3.4

  # Utilities
  intl: ^0.18.1
  url_launcher: ^6.2.1
  share_plus: ^7.2.1
  logger: ^2.0.2
  crypto: ^3.0.3

  # Dependency Injection
  get_it: ^7.6.4

  # Search
  flutter_typeahead: ^5.0.1

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
  build_runner: ^2.4.6
  hive_generator: ^2.0.1
```

### Package Usage Mapping

| Feature | Python Package | Flutter Package |
|---------|---------------|-----------------|
| HTTP Client | aiohttp | dio |
| HTML Parsing | BeautifulSoup | html |
| Terminal UI | Rich | Material/Cupertino |
| CLI Framework | Click | - (Native app) |
| Async File I/O | aiofiles | dart:io |
| Platform Dirs | platformdirs | path_provider |
| Video Player | mpv/VLC/IINA | video_player + chewie |
| Audio Player | - | just_audio |
| Image Viewer | - | photo_view |
| Fuzzy Search | pyfzf | flutter_typeahead |
| Secure Storage | - | flutter_secure_storage |
| Logging | Python logging | logger |
| Caching | Custom | hive / shared_preferences |

---

## 14. Migration Strategy

### Phase 1: Foundation (Week 1-2)

**Deliverables:**
- Project setup with clean architecture
- Data models implementation
- Network layer with retry logic
- Configuration management
- Basic error handling and logging

**Tasks:**
1. Create Flutter project with folder structure
2. Set up dependency injection (GetIt or Riverpod)
3. Implement all data models with JSON serialization
4. Create FTP HTTP client with Dio
5. Implement HTML parser
6. Create configuration manager
7. Set up secure storage for credentials
8. Implement logging system

### Phase 2: Core Features (Week 3-4)

**Deliverables:**
- Server selection and management
- File browser with navigation
- Caching system
- Download functionality

**Tasks:**
1. Create server selection UI
2. Implement add/edit/delete server screens
3. Build file browser screen with BLoC
4. Implement directory navigation
5. Create cache manager
6. Build download manager with progress tracking
7. Implement permission handling

### Phase 3: Media & Bookmarks (Week 5-6)

**Deliverables:**
- Media player integration
- Bookmark system
- Search functionality

**Tasks:**
1. Implement video player screen
2. Implement audio player screen
3. Implement image viewer
4. Create playlist functionality
5. Build bookmark manager
6. Create bookmark UI
7. Implement search with filtering

### Phase 4: Advanced Features (Week 7-8)

**Deliverables:**
- Batch operations
- Settings screen
- Polish and optimization

**Tasks:**
1. Implement multi-select mode
2. Create batch download/play actions
3. Build settings screen
4. Add theme support (dark/light)
5. Implement pull-to-refresh
6. Add loading states and shimmer effects
7. Performance optimization
8. Bug fixes and polish

### Phase 5: Testing & Release (Week 9-10)

**Deliverables:**
- Unit tests
- Widget tests
- Integration tests
- App store preparation

**Tasks:**
1. Write unit tests for business logic
2. Write widget tests for UI
3. Write integration tests for flows
4. Test on multiple devices
5. Prepare app store assets
6. Create documentation
7. Beta testing
8. Final release

---

## 15. Implementation Checklist

### Data Layer
- [ ] Server model with JSON serialization
- [ ] File/Folder models
- [ ] Bookmark model
- [ ] Cache entry model
- [ ] App session model

### Network Layer
- [ ] Dio HTTP client with interceptors
- [ ] Retry logic with exponential backoff
- [ ] HTML parsing
- [ ] Custom exceptions
- [ ] Authentication support
- [ ] Download manager with progress

### Business Logic
- [ ] File browser BLoC/StateNotifier
- [ ] Server management BLoC
- [ ] Download manager BLoC
- [ ] Bookmark manager BLoC
- [ ] Search BLoC
- [ ] Settings BLoC

### Data Sources
- [ ] Remote data source (HTTP)
- [ ] Local data source (cache)
- [ ] Configuration storage
- [ ] Bookmark storage
- [ ] Secure credential storage

### UI Screens
- [ ] Splash screen
- [ ] Server selection screen
- [ ] Add/Edit server screen
- [ ] File browser screen
- [ ] Video player screen
- [ ] Audio player screen
- [ ] Image viewer screen
- [ ] Bookmark list screen
- [ ] Download manager screen
- [ ] Search screen
- [ ] Settings screen

### UI Components
- [ ] Server list tile
- [ ] File/Folder list tile
- [ ] Breadcrumb navigation
- [ ] Batch selection mode
- [ ] Progress indicator
- [ ] Error dialogs
- [ ] Loading shimmer
- [ ] Pull-to-refresh

### Features
- [ ] Directory browsing
- [ ] Navigation (forward/back)
- [ ] File downloads
- [ ] Batch downloads
- [ ] Media playback
- [ ] Playlist support
- [ ] Bookmarks CRUD
- [ ] Search/filter
- [ ] Cache management
- [ ] Settings persistence

### Infrastructure
- [ ] Dependency injection
- [ ] Error handling
- [ ] Logging system
- [ ] Permission handling
- [ ] Deep linking (optional)
- [ ] Notifications
- [ ] Background tasks

### Testing
- [ ] Unit tests for models
- [ ] Unit tests for BLoCs
- [ ] Unit tests for repositories
- [ ] Widget tests for screens
- [ ] Integration tests for flows
- [ ] Performance tests

### Documentation
- [ ] Code documentation
- [ ] API documentation
- [ ] User guide
- [ ] README
- [ ] CHANGELOG

---

## Additional Recommendations

### Security Considerations

1. **Credential Storage**: Always use `flutter_secure_storage` for passwords
2. **HTTPS**: Warn users when connecting to non-HTTPS servers
3. **Input Validation**: Sanitize all user inputs
4. **URL Validation**: Validate URLs before connecting

### Performance Optimization

1. **Image Caching**: Use `cached_network_image` for thumbnails
2. **List Virtualization**: Use `ListView.builder` for large lists
3. **Lazy Loading**: Load directory contents on demand
4. **Debouncing**: Debounce search input
5. **Memory Management**: Dispose controllers properly

### UX Enhancements

1. **Offline Mode**: Show cached content when offline
2. **Smart Retry**: Auto-retry failed requests
3. **Undo Actions**: Allow undo for destructive actions
4. **Haptic Feedback**: Add haptic feedback for interactions
5. **Accessibility**: Support screen readers and large text

### Platform-Specific Features

**iOS:**
- Picture-in-Picture for video
- Handoff support
- Share sheet integration
- iCloud sync for bookmarks

**Android:**
- Android Auto support
- Picture-in-Picture
- Quick settings tile
- Storage Access Framework

**Web:**
- Deep linking with URL routes
- File download to browser
- Keyboard shortcuts

**Desktop:**
- Menu bar shortcuts
- Drag and drop support
- Multi-window support

---

## Conclusion

This guide provides a comprehensive roadmap for migrating the SAM-FTP CLI application to Flutter. The architecture is designed to be scalable, maintainable, and testable. Follow the phased migration strategy to ensure steady progress and early validation of core features.

Key success factors:
1. Start with solid data models and architecture
2. Implement network layer with proper error handling
3. Use state management consistently throughout
4. Test early and often
5. Optimize performance from the beginning
6. Design for cross-platform from day one

Good luck with your Flutter implementation! 🚀
