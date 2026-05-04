import SwiftUI

struct EntryTableView: View {
    @Bindable var store: BHEWorkspaceStore

    var body: some View {
        Group {
            if store.filteredEntries.isEmpty {
                ContentUnavailableView {
                    Label("No Parts Found", systemImage: "magnifyingglass")
                } description: {
                    Text("Adjust search or the View menu filters to bring more garage parts back into the service bay.")
                }
            } else {
                entryTable
            }
        }
        .navigationTitle(navigationTitle)
        .searchable(text: $store.searchText, prompt: "Search part names, service bays, formats, or offsets")
    }

    private var navigationTitle: String {
        if store.selectedGroupID == "all" {
            return "All Parts"
        }
        return store.groups.first { $0.id == store.selectedGroupID }?.title ?? "Entries"
    }

    private var entryTable: some View {
        Table(store.filteredEntries, selection: $store.selectedEntryID) {
            TableColumn("Name") { entry in
                Label(entry.name, systemImage: entry.kind.systemImage)
                    .lineLimit(1)
            }

            TableColumn("Service Bay") { entry in
                Text(entry.serviceBayDisplayName)
                    .lineLimit(1)
            }
            .width(min: 96, ideal: 112)

            TableColumn("Type") { entry in
                Text(entry.kind.displayName)
            }
            .width(min: 76, ideal: 92)

            TableColumn("Format") { entry in
                Text(entry.format)
                    .monospaced()
            }
            .width(min: 64, ideal: 76)

            TableColumn("Dimensions") { entry in
                Text(entry.dimensionsText)
                    .monospacedDigit()
            }
            .width(min: 92, ideal: 108)

            TableColumn("Palette") { entry in
                Text(entry.paletteText)
                    .monospacedDigit()
            }
            .width(min: 68, ideal: 78)

            TableColumn("Support") { entry in
                let support = EntryTableSupportDisplay(
                    entry: entry,
                    canExport3D: store.canExportEGameCar(entry),
                    isEGameSource: store.sourceKind?.isEGame == true
                )
                Label(support.title, systemImage: support.systemImage)
                    .labelStyle(.titleAndIcon)
                    .foregroundStyle(support.tint)
            }
            .width(min: 116, ideal: 136)

            TableColumn("Size") { entry in
                Text(entry.sizeText)
                    .monospacedDigit()
            }
            .width(min: 84, ideal: 96)

            TableColumn("Offset") { entry in
                Text(entry.offsetText)
                    .monospaced()
            }
            .width(min: 112, ideal: 128)
        }
        .contextMenu(forSelectionType: BHEEntry.ID.self) { selection in
            if let entry = firstEntry(in: selection) {
                Button("Generate Preview", systemImage: BHEWorkspaceAction.generatePreview.systemImage) {
                    perform(.generatePreview, using: selection)
                }

                Button("Open in Theatre View", systemImage: BHEWorkspaceAction.openTheatre.systemImage) {
                    perform(.openTheatre, using: selection)
                }
                .disabled(!store.canPerform(.openTheatre))

                Button("Quick Look Generated File", systemImage: BHEWorkspaceAction.quickLookPreview.systemImage) {
                    perform(.quickLookPreview, using: selection)
                }
                .disabled(!store.canPerform(.quickLookPreview))

                Divider()

                if entry.kind == .texture {
                    Button("Export Texture...", systemImage: BHEWorkspaceAction.extractSelected.systemImage) {
                        perform(.extractSelected, using: selection)
                    }
                    .disabled(!selectionCanExtract(selection))
                }

                if entry.kind == .model || entry.kind == .course || entry.kind == .field || entry.kind == .part {
                    Button(contextual3DExportTitle(for: entry), systemImage: BHEWorkspaceAction.export3DAsset.systemImage) {
                        perform(.export3DAsset, using: selection)
                    }
                    .disabled(!selectionCanExport3D(selection))
                }

                if entry.kind == .shop {
                    Button("Export Shop Textures...", systemImage: BHEWorkspaceAction.exportShopTextures.systemImage) {
                        perform(.exportShopTextures, using: selection)
                    }
                    .disabled(!selectionCanExportShopTextures(selection))
                }

                if entry.kind == .texture || entry.canReplace {
                    Button(BHEWorkspaceAction.validateReplacement.label, systemImage: BHEWorkspaceAction.validateReplacement.systemImage) {
                        perform(.validateReplacement, using: selection)
                    }
                    .disabled(!selectionCanReplace(selection))

                    Button(BHEWorkspaceAction.createPatchedCopy.label, systemImage: BHEWorkspaceAction.createPatchedCopy.systemImage) {
                        perform(.createPatchedCopy, using: selection)
                    }
                    .disabled(!selectionCanReplace(selection))
                }

                Divider()

                Button("Copy Name", systemImage: "doc.on.doc") {
                    selectFirstEntry(in: selection)
                    store.copySelectedName()
                }

                Button("Copy Offset", systemImage: "location.viewfinder") {
                    selectFirstEntry(in: selection)
                    store.copySelectedOffset()
                }

                Button("Copy Identifier", systemImage: "number") {
                    selectFirstEntry(in: selection)
                    store.copySelectedIdentifier()
                }

                Button("Copy Technical Details", systemImage: "text.magnifyingglass") {
                    selectFirstEntry(in: selection)
                    store.copyTechnicalDetails()
                }

                Button("Copy Manifest JSON", systemImage: "curlybraces") {
                    selectFirstEntry(in: selection)
                    store.copyManifestJSON()
                }
                .disabled(store.selectedPreviewManifest == nil)
            } else {
                Button("Select a Part", systemImage: "cursorarrow.click") { }
                    .disabled(true)
            }
        }
    }

    private func perform(_ action: BHEWorkspaceAction, using selection: Set<BHEEntry.ID>) {
        selectFirstEntry(in: selection)
        store.performAction(action)
    }

    private func selectFirstEntry(in selection: Set<BHEEntry.ID>) {
        guard let id = selection.first else {
            return
        }
        store.selectedEntryID = id
    }

    private func firstEntry(in selection: Set<BHEEntry.ID>) -> BHEEntry? {
        guard let id = selection.first else {
            return nil
        }
        return store.entries.first { $0.id == id }
    }

    private func contextual3DExportTitle(for entry: BHEEntry) -> String {
        switch entry.kind {
        case .model:
            return "Export Car Model..."
        case .course, .field:
            return "Export Scene Asset..."
        case .part:
            return "Export Part Asset..."
        default:
            return BHEWorkspaceAction.export3DAsset.label
        }
    }

    private func selectionCanExtract(_ selection: Set<BHEEntry.ID>) -> Bool {
        guard let entry = firstEntry(in: selection) else {
            return false
        }
        let isEGameSource = store.sourceKind?.isEGame == true
        return entry.canExtract && !isEGameSource
    }

    private func selectionCanExport3D(_ selection: Set<BHEEntry.ID>) -> Bool {
        guard let entry = firstEntry(in: selection) else {
            return false
        }
        return store.canExportEGameCar(entry)
    }

    private func selectionCanExportShopTextures(_ selection: Set<BHEEntry.ID>) -> Bool {
        guard let entry = firstEntry(in: selection) else {
            return false
        }
        return store.canExportEGameShopTextures(entry)
    }

    private func selectionCanReplace(_ selection: Set<BHEEntry.ID>) -> Bool {
        guard let entry = firstEntry(in: selection) else {
            return false
        }
        return entry.canReplace
    }
}

private struct EntryTableSupportDisplay {
    let title: String
    let systemImage: String
    let tint: Color

    init(entry: BHEEntry, canExport3D: Bool, isEGameSource: Bool) {
        if canExport3D {
            title = "3D Export"
            systemImage = BHEWorkspaceAction.export3DAsset.systemImage
            tint = QFactoryTheme.serviceGreen
        } else if entry.isExportableEGameShopTextures {
            title = "PNG Export"
            systemImage = BHEWorkspaceAction.exportShopTextures.systemImage
            tint = QFactoryTheme.serviceGreen
        } else if entry.canExtract && !isEGameSource {
            title = "PNG Export"
            systemImage = BHEWorkspaceAction.extractSelected.systemImage
            tint = QFactoryTheme.serviceGreen
        } else if entry.canReplace {
            title = "Replaceable"
            systemImage = BHEWorkspaceAction.validateReplacement.systemImage
            tint = QFactoryTheme.serviceGreen
        } else {
            switch entry.support {
            case .readOnly:
                title = "Inspect"
                systemImage = "eye"
                tint = QFactoryTheme.supportTint(for: entry.support)
            case .risky:
                title = "Needs Review"
                systemImage = entry.support.systemImage
                tint = QFactoryTheme.supportTint(for: entry.support)
            default:
                title = entry.support.displayName
                systemImage = entry.support.systemImage
                tint = QFactoryTheme.supportTint(for: entry.support)
            }
        }
    }
}
