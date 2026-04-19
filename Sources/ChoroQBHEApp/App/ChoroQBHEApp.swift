import SwiftUI

@main
struct ChoroQBHEApp: App {
    @State private var store = BHEWorkspaceStore(backend: MockBHEBackendClient())

    var body: some Scene {
        WindowGroup("Choro-Q BHE Tools") {
            ContentView(store: store)
                .frame(minWidth: 1040, minHeight: 680)
        }
        .defaultSize(width: 1180, height: 760)
        .commands {
            CommandGroup(after: .newItem) {
                Button("Load Sample Session") {
                    Task {
                        await store.loadSampleSession()
                    }
                }
                .keyboardShortcut("l", modifiers: [.command, .shift])
            }
        }
    }
}
