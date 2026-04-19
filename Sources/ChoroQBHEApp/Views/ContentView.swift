import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @Bindable var store: BHEWorkspaceStore
    @State private var isImportingISO = false

    private var isoTypes: [UTType] {
        [UTType(filenameExtension: "iso") ?? .data]
    }

    var body: some View {
        NavigationSplitView {
            SidebarView(store: store)
                .navigationSplitViewColumnWidth(min: 220, ideal: 260, max: 340)
        } content: {
            EntryTableView(store: store)
                .navigationSplitViewColumnWidth(min: 440, ideal: 560, max: 720)
        } detail: {
            EntryDetailView(store: store)
        }
        .toolbar {
            ToolbarItemGroup {
                Button {
                    isImportingISO = true
                } label: {
                    Label("Open ISO", systemImage: "opticaldiscdrive")
                }

                Button {
                    Task {
                        await store.loadSampleSession()
                    }
                } label: {
                    Label("Sample", systemImage: "sparkles")
                }
            }

            ToolbarItemGroup {
                Button {
                    store.markActionUnavailable("Extract")
                } label: {
                    Label("Extract", systemImage: "square.and.arrow.down")
                }
                .disabled(store.selectedEntry?.canExtract != true)

                Button {
                    store.markActionUnavailable("Replace")
                } label: {
                    Label("Replace", systemImage: "arrow.triangle.2.circlepath")
                }
                .disabled(store.selectedEntry?.canReplace != true)
            }
        }
        .fileImporter(
            isPresented: $isImportingISO,
            allowedContentTypes: isoTypes,
            allowsMultipleSelection: false
        ) { result in
            switch result {
            case .success(let urls):
                guard let url = urls.first else {
                    return
                }
                let didAccess = url.startAccessingSecurityScopedResource()
                Task {
                    await store.openISO(at: url)
                    if didAccess {
                        url.stopAccessingSecurityScopedResource()
                    }
                }
            case .failure(let error):
                store.errorMessage = error.localizedDescription
            }
        }
        .fileDialogMessage("Choose a PlayStation 2 ISO for a supported BHE Choro-Q game.")
        .safeAreaInset(edge: .bottom) {
            StatusBar(store: store)
        }
        .task {
            if store.entries.isEmpty {
                await store.loadSampleSession()
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
                Image(systemName: store.errorMessage == nil ? "info.circle" : "exclamationmark.triangle")
                    .foregroundStyle(store.errorMessage == nil ? Color.secondary : Color.orange)
            }

            Text(store.errorMessage ?? store.statusMessage)
                .foregroundStyle(store.errorMessage == nil ? .secondary : .primary)
                .lineLimit(1)

            Spacer()
        }
        .font(.footnote)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(.bar)
    }
}
