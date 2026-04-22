//
//  Q_s_FactoryApp.swift
//  Q's Factory
//
//  Created by Monty Giovenco on 19/4/2026.
//

import SwiftUI

@main
struct Q_s_FactoryApp: App {
    @State private var store = BHEWorkspaceStore(backend: ProcessBHEBackendClient())

    var body: some Scene {
        WindowGroup("Q's Factory") {
            ContentView(store: store)
                .frame(minWidth: 1040, minHeight: 680)
        }
        .defaultSize(width: 1180, height: 760)
        .commands {
            CommandGroup(replacing: .newItem) { }

            CommandGroup(after: .newItem) {
                Button("Open Garage Source...") {
                    Task { await store.openSourceWithPanel() }
                }
                .keyboardShortcut("o")

                Button("Close Garage Source") {
                    store.closeISO()
                }
                .disabled(!store.hasWorkspace)

                Divider()

                Button(BHEWorkspaceAction.extractSelected.label) {
                    store.performAction(.extractSelected)
                }
                .keyboardShortcut("e", modifiers: [.command, .shift])
                .disabled(!store.canPerform(.extractSelected))

                Button(BHEWorkspaceAction.extractContainer.label) {
                    store.performAction(.extractContainer)
                }
                .keyboardShortcut("e", modifiers: [.command, .option])
                .disabled(!store.canPerform(.extractContainer))

                Button(BHEWorkspaceAction.revealLastOutput.label) {
                    store.performAction(.revealLastOutput)
                }
                .disabled(!store.canPerform(.revealLastOutput))
            }

            CommandGroup(after: .pasteboard) {
                Button("Copy Name") {
                    store.copySelectedName()
                }
                .keyboardShortcut("c", modifiers: [.command, .shift])
                .disabled(store.selectedEntry == nil)

                Button("Copy Offset") {
                    store.copySelectedOffset()
                }
                .keyboardShortcut("c", modifiers: [.command, .option])
                .disabled(store.selectedEntry == nil)

                Button("Copy Identifier") {
                    store.copySelectedIdentifier()
                }
                .keyboardShortcut("c", modifiers: [.command, .control])
                .disabled(store.selectedEntry == nil)
            }

            CommandGroup(after: .toolbar) {
                Button(store.isInspectorPresented ? "Hide Inspector" : "Show Inspector") {
                    store.isInspectorPresented.toggle()
                }
                .keyboardShortcut("i", modifiers: [.command, .option])

                Divider()

                Picker("Preview Background", selection: $store.previewBackground) {
                    ForEach(BHEPreviewBackground.allCases) { background in
                        Text(background.displayName).tag(background)
                    }
                }
                .disabled(store.selectedEntry?.kind != .texture)

                Toggle("Show Unsupported Entries", isOn: $store.showUnsupportedEntries)
                    .disabled(!store.hasWorkspace)

                Toggle("Show Compressed Entries", isOn: $store.showCompressedEntries)
                    .disabled(!store.hasWorkspace)
            }

            CommandMenu("Operations") {
                Button(BHEWorkspaceAction.validateReplacement.label) {
                    store.performAction(.validateReplacement)
                }
                .keyboardShortcut("v", modifiers: [.command, .option])
                .disabled(!store.canPerform(.validateReplacement))

                Button(BHEWorkspaceAction.createPatchedCopy.label) {
                    store.performAction(.createPatchedCopy)
                }
                .keyboardShortcut("r", modifiers: [.command, .option])
                .disabled(!store.canPerform(.createPatchedCopy))

                Divider()

                Button(BHEWorkspaceAction.verifyISO.label) {
                    store.performAction(.verifyISO)
                }
                .disabled(!store.canPerform(.verifyISO))

                Button(BHEWorkspaceAction.exportOperationLog.label) {
                    store.performAction(.exportOperationLog)
                }
                .disabled(!store.canPerform(.exportOperationLog))
            }

            CommandGroup(after: .help) {
                Button("Backend Diagnostics...") {
                    store.showBackendDiagnostics()
                }

                Button("Interaction Design Notes") {
                    store.openDesignNotes()
                }
            }
        }
    }
}
