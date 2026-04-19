import SwiftUI

struct EntryTableView: View {
    @Bindable var store: BHEWorkspaceStore

    var body: some View {
        Table(store.filteredEntries, selection: $store.selectedEntryID) {
            TableColumn("Name") { entry in
                Label(entry.name, systemImage: entry.kind.systemImage)
                    .lineLimit(1)
            }

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
        .navigationTitle(store.selectedGroupID == "all" ? "All Entries" : store.selectedGroupID)
        .contextMenu(forSelectionType: BHEEntry.ID.self) { selection in
            Button("Extract", systemImage: "square.and.arrow.down") {
                store.markActionUnavailable("Extract")
            }
            .disabled(!selectionCanExtract(selection))

            Button("Replace Texture", systemImage: "arrow.triangle.2.circlepath") {
                store.markActionUnavailable("Replace")
            }
            .disabled(!selectionCanReplace(selection))
        }
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
