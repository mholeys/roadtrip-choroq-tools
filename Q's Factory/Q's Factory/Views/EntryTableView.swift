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
                Text(entry.cpkName)
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
                Label(entry.support.displayName, systemImage: entry.support.systemImage)
                    .labelStyle(.titleAndIcon)
                    .foregroundStyle(QFactoryTheme.supportTint(for: entry.support))
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
            Button(BHEWorkspaceAction.extractSelected.label, systemImage: BHEWorkspaceAction.extractSelected.systemImage) {
                perform(.extractSelected, using: selection)
            }
            .disabled(!selectionCanExtract(selection))

            Button(BHEWorkspaceAction.validateReplacement.label, systemImage: BHEWorkspaceAction.validateReplacement.systemImage) {
                perform(.validateReplacement, using: selection)
            }
            .disabled(!selectionCanReplace(selection))

            Button(BHEWorkspaceAction.createPatchedCopy.label, systemImage: BHEWorkspaceAction.createPatchedCopy.systemImage) {
                perform(.createPatchedCopy, using: selection)
            }
            .disabled(!selectionCanReplace(selection))

            Divider()

            Button("Copy Name", systemImage: "doc.on.doc") {
                selectFirstEntry(in: selection)
                store.copySelectedName()
            }
            .disabled(selection.isEmpty)

            Button("Copy Offset") {
                selectFirstEntry(in: selection)
                store.copySelectedOffset()
            }
            .disabled(selection.isEmpty)

            Button("Copy Identifier") {
                selectFirstEntry(in: selection)
                store.copySelectedIdentifier()
            }
            .disabled(selection.isEmpty)
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

    private func selectionCanExtract(_ selection: Set<BHEEntry.ID>) -> Bool {
        guard let id = selection.first,
              let entry = store.entries.first(where: { $0.id == id }) else {
            return false
        }
        return entry.canExtract
    }

    private func selectionCanReplace(_ selection: Set<BHEEntry.ID>) -> Bool {
        guard let id = selection.first,
              let entry = store.entries.first(where: { $0.id == id }) else {
            return false
        }
        return entry.canReplace
    }
}
