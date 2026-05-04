import SwiftUI
import QuickLookUI

struct ContentView: View {
    @Bindable var store: BHEWorkspaceStore
    @State private var isSourceDropTargeted = false

    var body: some View {
        NavigationSplitView {
            SidebarView(store: store)
                .navigationSplitViewColumnWidth(min: 220, ideal: 260, max: 340)
        } detail: {
            Group {
                if store.hasWorkspace {
                    EntryTableView(store: store)
                } else {
                    EmptyWorkspaceView(store: store, isDropTargeted: isSourceDropTargeted)
                }
            }
            .inspector(isPresented: $store.isInspectorPresented) {
                EntryDetailView(store: store)
                    .inspectorColumnWidth(min: 300, ideal: 360, max: 460)
            }
        }
        .toolbar { appToolbar }
        .tint(QFactoryTheme.factoryBlue)
        .alert(
            store.userError?.title ?? "Operation Failed",
            isPresented: Binding(
                get: { store.userError != nil },
                set: { isPresented in
                    if !isPresented {
                        store.userError = nil
                    }
                }
            )
        ) {
            Button("OK") {
                store.userError = nil
            }
        } message: {
            if let userError = store.userError {
                Text(errorMessage(for: userError))
            }
        }
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 0) {
                if store.playbackState.isActive, let item = store.activeAudioItem {
                    MiniPlayerView(item: item, playbackState: store.playbackState)
                }
                StatusBar(store: store)
            }
        }
        .sheet(isPresented: $store.isBackendDiagnosticsPresented) {
            BackendDiagnosticsView(store: store)
        }
        .sheet(
            isPresented: Binding(
                get: { store.quickLookURL != nil },
                set: { isPresented in
                    if !isPresented {
                        store.quickLookURL = nil
                    }
                }
            )
        ) {
            if let quickLookURL = store.quickLookURL {
                QuickLookPreviewSheet(url: quickLookURL)
            }
        }
        .sheet(item: $store.theatrePreviewItem) { item in
            TheatrePreviewView(item: item, store: store)
        }
        .sheet(item: $store.verboseConsoleOperation) { operation in
            VerboseConsoleView(operation: operation)
        }
        .dropDestination(for: URL.self) { urls, _ in
            guard let url = urls.first else {
                return false
            }
            Task { await store.openSource(at: url) }
            return true
        } isTargeted: { isTargeted in
            isSourceDropTargeted = isTargeted
        }
    }

    @ToolbarContentBuilder
    private var appToolbar: some ToolbarContent {
        ToolbarItemGroup {
            Button {
                Task { await store.openSourceWithPanel() }
            } label: {
                Label("Open Garage", systemImage: "externaldrive.badge.plus")
            }
            .help("Choose an ISO, BIN/CUE pair, or mounted source folder for the garage.")

            Button {
                store.closeISO()
            } label: {
                Label("Close Garage", systemImage: "xmark.circle")
            }
            .disabled(!store.hasWorkspace)
            .help("Close the current source and clear the service bay.")
        }

        ToolbarItemGroup {
            contextualExportButton

            Button {
                store.performAction(.generatePreview)
            } label: {
                Label("Preview", systemImage: BHEWorkspaceAction.generatePreview.systemImage)
            }
            .disabled(!store.canPerform(.generatePreview))
            .help(store.helpText(for: .generatePreview))

            Button {
                store.performAction(.openTheatre)
            } label: {
                Label("Theatre", systemImage: BHEWorkspaceAction.openTheatre.systemImage)
            }
            .disabled(!store.canPerform(.openTheatre))
            .help(store.helpText(for: .openTheatre))

            Button {
                store.performAction(.quickLookPreview)
            } label: {
                Label("Quick Look", systemImage: BHEWorkspaceAction.quickLookPreview.systemImage)
            }
            .disabled(!store.canPerform(.quickLookPreview))
            .help(store.helpText(for: .quickLookPreview))
        }

        ToolbarItemGroup(placement: .primaryAction) {
            Button {
                store.isInspectorPresented.toggle()
            } label: {
                Label(store.isInspectorPresented ? "Hide Inspector" : "Show Inspector", systemImage: "sidebar.right")
            }
            .help("Show or hide the preview and metadata inspector.")
        }
    }

    @ViewBuilder
    private var contextualExportButton: some View {
        if store.selectedEntry?.kind == .texture {
            Button {
                store.performAction(.extractSelected)
            } label: {
                Label("Export Texture", systemImage: BHEWorkspaceAction.extractSelected.systemImage)
            }
            .disabled(!store.canPerform(.extractSelected))
            .help(textureExportHelpText)
        } else if store.selectedEntry?.kind == .shop {
            Button {
                store.performAction(.exportShopTextures)
            } label: {
                Label("Export Shop Textures", systemImage: BHEWorkspaceAction.exportShopTextures.systemImage)
            }
            .disabled(!store.canPerform(.exportShopTextures))
            .help(store.helpText(for: .exportShopTextures))
        } else {
            Button {
                store.performAction(.export3DAsset)
            } label: {
                Label(export3DTitle, systemImage: BHEWorkspaceAction.export3DAsset.systemImage)
            }
            .disabled(!store.canPerform(.export3DAsset))
            .help(store.helpText(for: .export3DAsset))
        }
    }

    private var export3DTitle: String {
        guard let entry = store.selectedEntry else {
            return "Export Asset"
        }
        switch entry.kind {
        case .model:
            return "Export Car Model"
        case .course, .field:
            return "Export Scene Asset"
        case .part:
            return "Export Part Asset"
        default:
            return "Export 3D Asset"
        }
    }

    private var replacementValidationTitle: String {
        store.selectedEntry?.kind == .texture ? "Validate Texture Replacement" : "Validate Replacement"
    }

    private var textureExportHelpText: String {
        if store.sourceKind?.isEGame == true {
            return "Road Trip / HG2 / HG3 texture export is not connected for this row."
        }
        return store.helpText(for: .extractSelected)
    }

    private func errorMessage(for error: BHEUserFacingError) -> String {
        var parts = [error.explanation]
        if let suggestion = error.suggestion {
            parts.append(suggestion)
        }
        if let relatedEntryID = error.relatedEntryID {
            parts.append("Entry: \(relatedEntryID)")
        }
        if let technicalDetails = error.technicalDetails {
            parts.append("Details: \(technicalDetails)")
        }
        return parts.joined(separator: "\n\n")
    }
}

private struct EmptyWorkspaceView: View {
    let store: BHEWorkspaceStore
    let isDropTargeted: Bool

    var body: some View {
        ZStack {
            QFactoryTheme.workbenchTint

            VStack(spacing: 22) {
                VStack(spacing: 12) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 8)
                            .fill(QFactoryTheme.factoryBlue)
                        Image(systemName: "wrench.and.screwdriver")
                            .font(.system(size: 34, weight: .semibold))
                            .foregroundStyle(.white)
                    }
                    .frame(width: 72, height: 72)
                    .overlay(alignment: .topTrailing) {
                        Circle()
                            .fill(QFactoryTheme.factoryRed)
                            .frame(width: 18, height: 18)
                            .overlay {
                                Circle()
                                    .stroke(.white, lineWidth: 2)
                            }
                            .offset(x: 5, y: -5)
                    }

                    Text("Q's Factory")
                        .font(.largeTitle.weight(.semibold))

                    Text("Open a supported Choro-Q source to inspect service bays, formats, textures, model records, offsets, and safe export actions.")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: 540)
                }

                SupportedSourcesStrip()

                Button {
                    Task { await store.openSourceWithPanel() }
                } label: {
                    Label("Open Garage Source...", systemImage: "folder.badge.plus")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .help("Choose an ISO, BIN/CUE pair, or mounted source folder.")
            }
            .padding(40)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .overlay {
            if isDropTargeted {
                RoundedRectangle(cornerRadius: 8)
                    .stroke(QFactoryTheme.factoryBlue, style: StrokeStyle(lineWidth: 4, dash: [10, 8]))
                    .padding(24)
                    .allowsHitTesting(false)
            }
        }
        .navigationTitle("Garage")
    }
}

private struct SupportedSourcesStrip: View {
    private let sources = [
        ("ISO", "opticaldiscdrive", QFactoryTheme.factoryBlue),
        ("Mounted Disc", "externaldrive", QFactoryTheme.serviceGreen),
        ("BIN/CUE", "record.circle", QFactoryTheme.hazardYellow),
    ]

    var body: some View {
        HStack(spacing: 12) {
            ForEach(sources, id: \.0) { source in
                Label(source.0, systemImage: source.1)
                    .font(.callout.weight(.medium))
                    .foregroundStyle(source.2)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(QFactoryTheme.panelFill, in: .rect(cornerRadius: 8))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(QFactoryTheme.panelStroke, lineWidth: 1)
                    }
            }
        }
    }
}

private struct MiniPlayerView: View {
    let item: AssetAudioItem
    let playbackState: PlaybackState

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: playbackStateIcon)
                .foregroundStyle(QFactoryTheme.factoryBlue)
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title)
                    .font(.footnote.weight(.medium))
                    .lineLimit(1)
                Text(item.sourceFormat)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            Text(durationText)
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 7)
        .background(.regularMaterial)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(.separator)
                .frame(height: 1)
        }
    }

    private var playbackStateIcon: String {
        switch playbackState {
        case .playing:
            "pause.circle"
        case .paused:
            "play.circle"
        case .loading:
            "clock"
        case .failed:
            "xmark.octagon"
        case .stopped:
            "stop.circle"
        }
    }

    private var durationText: String {
        guard let duration = item.duration else {
            return "--:--"
        }
        let seconds = Int(duration.rounded())
        return String(format: "%d:%02d", seconds / 60, seconds % 60)
    }
}

private struct QuickLookPreviewSheet: View {
    let url: URL

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Label(url.lastPathComponent, systemImage: "eye")
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
            }
            .padding()
            .background(.bar)

            QuickLookPreviewBridge(url: url)
                .frame(minWidth: 720, minHeight: 520)
        }
    }
}

private struct QuickLookPreviewBridge: NSViewRepresentable {
    let url: URL

    func makeNSView(context: Context) -> QLPreviewView {
        let view = QLPreviewView(frame: .zero, style: .normal)!
        view.autostarts = true
        view.previewItem = url as NSURL
        return view
    }

    func updateNSView(_ view: QLPreviewView, context: Context) {
        view.previewItem = url as NSURL
    }
}

private struct TheatrePreviewView: View {
    let item: TheatrePreviewItem
    let store: BHEWorkspaceStore

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Label(item.title, systemImage: item.kind.systemImage)
                    .font(.headline)
                Spacer()
                Button {
                    store.quickLookCurrentPreview()
                } label: {
                    Label("Quick Look", systemImage: "eye")
                }
                .disabled(item.url == nil)
            }
            .padding()
            .background(.bar)

            Group {
                switch item.kind {
                case .modelScene:
                    ScenePreviewView(
                        entry: store.selectedEntry ?? placeholderEntry,
                        modelURL: item.url,
                        manifest: item.manifest,
                        previewState: store.previewState,
                        isLoading: false,
                        failureMessage: nil,
                        relinkReport: store.materialRelinkReport
                    )
                    .padding()
                case .rasterImage:
                    RasterPreviewView(
                        entry: store.selectedEntry ?? placeholderEntry,
                        background: store.previewBackground,
                        previewURL: item.url,
                        previewState: store.previewState,
                        isLoading: false,
                        failureMessage: nil
                    )
                    .padding()
                default:
                    ContentUnavailableView("Theatre View", systemImage: item.kind.systemImage, description: Text("This preview type is not available in theatre mode yet."))
                }
            }
            .frame(minWidth: 760, minHeight: 520)
        }
    }

    private var placeholderEntry: BHEEntry {
        BHEEntry(
            id: item.entryID,
            containerID: "",
            cpkName: "",
            serviceBayName: nil,
            name: item.title,
            kind: .unknown,
            format: "",
            width: nil,
            height: nil,
            paletteSize: nil,
            sizeBytes: 0,
            offsetBytes: -1,
            sector: -1,
            support: .unknown,
            canExtract: false,
            canReplace: false,
            compression: "",
            meshCount: nil,
            textureCount: nil,
            descriptor: nil,
            modelDescription: nil,
            expectedExportOutputs: nil,
            supportReason: nil,
            unsupportedReason: nil,
            sectionNames: nil,
            partSectionNames: nil,
            supportedOperations: nil
        )
    }
}

private struct VerboseConsoleView: View {
    let operation: VerboseConsoleOperation

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Label(operation.title, systemImage: "terminal")
                .font(.headline)
                .padding()
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    consoleLine("Operation", operation.id)
                    if let entryID = operation.entryID {
                        consoleLine("Entry", entryID)
                    }
                    if let manifest = operation.manifest {
                        consoleLine("Generated Files", "\(manifest.files.count)")
                        consoleLine("Source Modified", "\(manifest.sourceModified)")
                        consoleLine("Patched Copy Written", "\(manifest.patchedCopyWritten)")
                    }
                    ForEach(operation.diagnostics) { diagnostic in
                        consoleLine(diagnostic.title, diagnostic.detail)
                    }
                    if let relinkReport = operation.relinkReport {
                        consoleLine("Material Relink", relinkReport.summary)
                    }
                    if !operation.logEntries.isEmpty {
                        Text("Operation Log")
                            .font(.headline)
                        ForEach(operation.logEntries) { log in
                            Text("\(log.level.rawValue): \(log.title)")
                                .font(.caption.monospaced())
                                .textSelection(.enabled)
                        }
                    }
                }
                .padding()
            }
            .font(.system(.body, design: .monospaced))
        }
        .frame(minWidth: 680, minHeight: 520)
    }

    private func consoleLine(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(value)
                .textSelection(.enabled)
        }
    }
}

private struct StatusBar: View {
    let store: BHEWorkspaceStore

    var body: some View {
        HStack(spacing: 8) {
            if store.isLoading {
                ProgressView()
                    .controlSize(.small)
            } else {
                Image(systemName: store.userError == nil ? "info.circle" : "exclamationmark.triangle")
                    .foregroundStyle(store.userError == nil ? QFactoryTheme.factoryBlue : QFactoryTheme.hazardYellow)
            }

            Text(store.statusMessage)
                .foregroundStyle(store.userError == nil ? .secondary : .primary)
                .lineLimit(1)

            Spacer()
        }
        .font(.footnote)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(.bar)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(.separator)
                .frame(height: 1)
        }
    }
}
