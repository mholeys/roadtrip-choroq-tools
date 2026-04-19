import Foundation
import Observation

@MainActor
@Observable
final class BHEWorkspaceStore {
    private let backend: BHEBackendClient

    var isoSummary: BHEISOSummary?
    var entries: [BHEEntry] = []
    var selectedGroupID = "all"
    var selectedEntryID: BHEEntry.ID?
    var isLoading = false
    var statusMessage = "Load a sample session or open an ISO to inspect BHE assets."
    var errorMessage: String?

    init(backend: BHEBackendClient) {
        self.backend = backend
    }

    var groups: [BHEEntryGroup] {
        let grouped = Dictionary(grouping: entries, by: \.cpkName)
        let cpkGroups = grouped.keys.sorted().map { cpkName in
            BHEEntryGroup(
                id: cpkName,
                title: cpkName,
                detail: "\(grouped[cpkName, default: []].count) entries",
                systemImage: "shippingbox"
            )
        }

        return [
            BHEEntryGroup(
                id: "all",
                title: "All Entries",
                detail: "\(entries.count) entries",
                systemImage: "square.grid.2x2"
            )
        ] + cpkGroups
    }

    var filteredEntries: [BHEEntry] {
        guard selectedGroupID != "all" else {
            return entries
        }
        return entries.filter { $0.cpkName == selectedGroupID }
    }

    var selectedEntry: BHEEntry? {
        guard let selectedEntryID else {
            return nil
        }
        return entries.first { $0.id == selectedEntryID }
    }

    @MainActor
    func loadSampleSession() async {
        await performLoad {
            try await backend.loadSampleSession()
        }
    }

    @MainActor
    func openISO(at url: URL) async {
        await performLoad {
            try await backend.scanISO(at: url)
        }
    }

    @MainActor
    func markActionUnavailable(_ action: String) {
        statusMessage = "\(action) will be wired after the Python JSON bridge is added."
    }

    @MainActor
    private func performLoad(_ operation: () async throws -> BHEScanResult) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let result = try await operation()
            isoSummary = result.iso
            entries = result.entries
            selectedGroupID = "all"
            selectedEntryID = result.entries.first?.id
            statusMessage = "Loaded \(result.iso.isoName): \(result.entries.count) entries."
        } catch {
            errorMessage = error.localizedDescription
            statusMessage = "Load failed."
        }
    }
}
