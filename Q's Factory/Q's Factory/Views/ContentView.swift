import SwiftUI

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
            StatusBar(store: store)
        }
        .sheet(isPresented: $store.isBackendDiagnosticsPresented) {
            BackendDiagnosticsView(store: store)
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
            Button {
                store.performAction(.extractSelected)
            } label: {
                Label("Extract Part", systemImage: BHEWorkspaceAction.extractSelected.systemImage)
            }
            .disabled(!store.canPerform(.extractSelected))
            .help(store.helpText(for: .extractSelected))

            Button {
                store.performAction(.validateReplacement)
            } label: {
                Label("Validate Replacement", systemImage: BHEWorkspaceAction.validateReplacement.systemImage)
            }
            .disabled(!store.canPerform(.validateReplacement))
            .help(store.helpText(for: .validateReplacement))

            Button {
                store.performAction(.createPatchedCopy)
            } label: {
                Label("Create Patched Copy", systemImage: BHEWorkspaceAction.createPatchedCopy.systemImage)
            }
            .disabled(!store.canPerform(.createPatchedCopy))
            .help(store.helpText(for: .createPatchedCopy))
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
