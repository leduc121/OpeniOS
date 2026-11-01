# OpeniOS Live Preview Desktop Application

A native Ubuntu desktop simulator providing Apple iPhone hardware profiles and an embedded interactive WebKit engine with Hot Module Reloading (HMR) for modern web and mobile frameworks.

---

## 1. Product Overview

OpeniOS Live Preview runs as a standalone native Linux desktop application designed for developers working in VS Code, Antigravity, or terminal on Ubuntu:

```
Ubuntu (Wayland / X11)
  └─► OpeniOS Simulator
        ├─► Standalone iPhone 14 Pro Max Window (Dynamic Island, Bezel, Home Indicator)
        ├─► Embedded Interactive WebKit Engine (Touch, Scroll, Input)
        └─► Framework Dev Server Live Connection (React/Vite HMR, Expo Web, Flutter Web)
```

> **Important Architectural Boundary:**  
> **OpeniOS Live Preview** provides high-speed web-rendered mobile previews inside a native desktop window. It is explicitly separated from the **Native Emulator (`QEMU-SPTM`)** backend, which virtualizes genuine Darwin/iOS guest kernels and graphics services. WebKit rendering is NOT claimed as genuine guest iOS rendering.

---

## 2. Implemented Features

### P0 — Standalone iPhone Window & Engine (PASS)
- **Native Wayland / Hyprland desktop window** (`OpenIOSApplication`, `SimulatorWindow`).
- **High-fidelity hardware bezel** rendered in hardware-accelerated Cairo:
  - Authentic display corner radius mask (`cairo.FILL_RULE_EVEN_ODD`).
  - Dark brushed titanium chassis with subtle metallic reflections.
  - Side buttons (Action Button, Volume Up, Volume Down, Side/Power Button).
  - Top speaker slit.
  - **Dynamic Island** pill cutout with front camera aperture and lens optical reflections.
  - **Home Indicator** floating bottom pill bar with pass-through interaction (`Gtk.Overlay.set_overlay_pass_through`).
- **Data-driven Device Presets**:
  - `iPhone 14 Pro Max` (430 × 932 pt, 3.0× scale, radius 55px).
  - `iPhone 15` (393 × 852 pt, 3.0× scale, radius 47px).
  - `iPhone 15 Pro Max` (430 × 932 pt, 3.0× scale, radius 55px, slim titanium bezel).
- **Interactive Embedded WebKit2**:
  - iPhone Mobile Safari User-Agent.
  - Injected CSS environment safe-area variables (`--sat`, `--sab`, `--sal`, `--sar`).
  - Zoom levels: 50%, 75%, 85%, 100%.
  - Orientation toggling (Portrait / Landscape).
  - Touch, click, keyboard typing, and smooth scrolling.

### P1 — Project Detection & React/Vite Preview with HMR (PASS)
- **Automatic project detection**:
  - Inspects `package.json` dependencies and scripts.
  - Selects package manager (`npm`, `pnpm`, `yarn`, `bun`).
- **Isolated Process Management**:
  - Binds strictly to `127.0.0.1` (no public exposure).
  - Non-shell subprocess argument arrays with distinct process groups (`os.setsid`).
  - Real-time stdout/stderr stream parsing for dev-server readiness and port detection.
  - Collapsible dev server console drawer.
  - Clean shutdown of process tree (`SIGTERM` -> `SIGKILL` bounded termination).
- **Vite Hot Module Reloading (HMR)**:
  - Preserves Vite's native WebSocket HMR connection.
  - Verified live component updates on source edit without restarting OpeniOS or losing state.

### P2 — Expo Web & Flutter Web Multi-Framework Support (PASS)
- **Expo Web Adapter**:
  - Detects Expo projects (`expo` in dependencies).
  - Launches `npx expo start --web --localhost`.
  - Captures Metro bundler URL and displays Fast Refresh logs.
  - Accurately reports unsupported native iOS modules on the web target.
- **Flutter Web Adapter**:
  - Detects `pubspec.yaml` and verifies Flutter SDK availability.
  - Automatically identifies available ports avoiding conflicts (`find_available_port`).
  - Launches `flutter run -d web-server --web-port <port> --web-hostname 127.0.0.1`.
  - Supports incremental reload via interactive input (`r\n`) to dev-server stdin.
  - Truthful compatibility report: Flutter web-server mode provides incremental compilation; full state-preserving debugging requires Dart Debug transport.

---

## 3. Directory Layout

```
openios/live_preview/
├── __init__.py
├── main.py                     # CLI entrypoint and auto-reexec launcher
├── app.py                      # Gtk.Application lifecycle & CSS styles
├── window.py                   # Standalone iPhone window & toolbar
├── core/
│   ├── models.py               # BackendType, Orientation, ServerState, DeviceProfile
│   ├── project.py              # ProjectManager for directory inspection
│   ├── framework_detector.py   # Automatic framework detector
│   └── process_manager.py      # Subprocess lifecycle & port detection
├── devices/
│   ├── profiles.py             # iPhone 14 Pro Max, 15, 15 Pro Max specs
│   └── registry.py             # Device registry lookup
├── adapters/
│   ├── base.py                 # BaseFrameworkAdapter interface
│   ├── registry.py             # Adapter registry
│   ├── vite_react.py           # React + Vite adapter (HMR)
│   ├── expo_web.py             # Expo Web adapter (Fast Refresh)
│   ├── flutter_web.py          # Flutter Web adapter
│   └── static_web.py           # Static HTML5/CSS3/JS adapter
├── preview/
│   └── webview.py              # WebKit2 WebView with iPhone mobile profile
├── ui/
│   ├── device_frame.py         # Hardware chassis, bezel, Dynamic Island, Home indicator
│   ├── toolbar.py              # Modern simulator toolbar
│   └── log_viewer.py           # Dev server console drawer
├── assets/
│   ├── style.css               # Modern dark theme
│   └── welcome.html            # Default interactive welcome page
├── tests/
│   ├── test_devices.py         # Geometry and preset tests
│   ├── test_detector.py        # Framework and package manager tests
│   ├── test_adapters.py        # Adapter validation tests
│   ├── test_process_manager.py # Process lifecycle and URL regex tests
│   └── fixtures/               # Test fixtures (React+Vite, Expo, Flutter)
└── README.md
```

---

## 4. Host Environment & Installation

### Verified Host Environment
- **OS**: Ubuntu 26.04.1 LTS (x86_64)
- **Display Protocol**: Wayland (Hyprland / GNOME Shell)
- **Python**: Python 3.14 (system `/usr/bin/python3`)
- **Libraries**: GTK 3.0, WebKit2 4.1 (`WebKit2-4.1.typelib`), PyCairo
- **Toolchains**: Node.js v22.23.2, npm 10.9.8, Flutter 3.47.4

### Required Packages (Ubuntu)
```bash
# Core desktop GUI and WebKit bindings
sudo apt update
sudo apt install -y python3-gi gir1.2-webkit2-4.1 python3-cairo libgtk-3-0
```

> *Note:* If running inside a Conda or isolated virtualenv that lacks PyGObject bindings, `main.py` automatically detects this and re-executes using `/usr/bin/python3`.

---

## 5. Usage Instructions

### 1. Launch with Default Interactive iPhone Window
```bash
./openios/live_preview/main.py
```
*Opens the standalone iPhone 14 Pro Max window with the interactive touch & keyboard test page.*

### 2. Launch with a React + Vite Project
```bash
./openios/live_preview/main.py --project openios/live_preview/tests/fixtures/react_vite_sample
```
*Automatically detects React + Vite, launches `npm run dev -- --host 127.0.0.1`, streams dev server logs into the console drawer, and establishes live Vite HMR.*

### 3. Launch with Specific Device Model and Zoom
```bash
./openios/live_preview/main.py --device iphone-15-pro-max --zoom 0.75
```

### 4. Run Smoke Test (Non-GUI CI validation)
```bash
./openios/live_preview/main.py --test-smoke
```

---

## 6. Running Automated Tests

Run all unit tests across models, framework detection, adapters, and process lifecycle:

```bash
/usr/bin/python3 -m unittest discover -s openios/live_preview/tests -v
```

All 15 tests execute in <0.3s and validate:
- Profile dimensions, safe-area insets, and portrait/landscape calculations.
- Framework detection for React+Vite, generic Vite, Expo, Flutter, and Static HTML.
- Package manager resolution (`npm`, `pnpm`, `yarn`, `bun`).
- Subprocess process group cleanup and URL readiness matching.

---

## 7. Multi-Framework Compatibility Report

| Framework | Dev Server Command | Detected URL | Live Update Mode | State Preservation | Notes / Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **React + Vite** | `npm run dev -- --host 127.0.0.1` | `http://127.0.0.1:5173/` | **Vite HMR (WebSocket)** | **Yes (React state preserved)** | Fully verified; instant update on source edit. |
| **Expo Web** | `npx expo start --web --localhost` | `http://127.0.0.1:8081/` | **Expo Fast Refresh** | **Yes (Web runtime)** | Requires `react-native-web`. Native iOS-only pods require web fallbacks. |
| **Flutter Web** | `flutter run -d web-server --web-port <p> --web-hostname 127.0.0.1` | `http://127.0.0.1:<port>/` | **Incremental Compile** | **Partial (Full restart)** | Triggered via `r` key on dev-server stdin. Full state preservation requires Dart Debug transport. |
| **Static Web** | `python3 -m http.server <port> --bind 127.0.0.1` | `http://127.0.0.1:<port>/` | **Manual / WebKit Reload** | **No (Static server)** | Reliable fallback for pure HTML/CSS/JS without bundlers. |

---

## 8. Safety & Isolation Guarantee

- All Live Preview code is isolated in `openios/live_preview/`.
- Existing research branch (`openios/display-research`) and QEMU-SPTM firmware files remain untouched.
- No git commits, pushes, merges, or rebases were performed.
