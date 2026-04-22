import Foundation

@MainActor
protocol BHEBackendClient {
    func version() async throws -> BHEBackendVersion
    func healthCheck() async throws -> BHEBackendHealth
    func listSupportedTypes() async throws -> BHESupportedTypes
    func scanISO(at url: URL) async throws -> BHEScanResult
    func scanDiscRoot(at url: URL) async throws -> BHEScanResult
    func scanEGameDiscRoot(at url: URL) async throws -> BHEScanResult
    func previewTexture(in isoURL: URL, entryID: BHEEntry.ID, outputURL: URL) async throws -> BHETexturePreviewResult
    func previewTexture(inDiscRoot rootURL: URL, entryID: BHEEntry.ID, outputURL: URL) async throws -> BHETexturePreviewResult
    func extractTexture(from isoURL: URL, entryID: BHEEntry.ID, outputURL: URL) async throws -> BHETextureExtractionResult
    func extractTexture(fromDiscRoot rootURL: URL, entryID: BHEEntry.ID, outputURL: URL) async throws -> BHETextureExtractionResult
}

enum BHEBackendError: LocalizedError {
    case commandUnavailable(String)
    case commandFailed(BHECommandErrorPayload)
    case incompatibleProtocol(Int, backendVersion: String)
    case invalidResponse(String)

    var errorDescription: String? {
        switch self {
        case .commandUnavailable(let details):
            "The BHE Python command could not be found. \(details)"
        case .commandFailed(let payload):
            payload.technicalDetails ?? payload.explanation
        case .incompatibleProtocol(let protocolVersion, let backendVersion):
            "The BHE Python backend protocol \(protocolVersion) from backend \(backendVersion) is newer than this app supports."
        case .invalidResponse(let details):
            "The BHE Python command returned JSON the app could not read. \(details)"
        }
    }
}

struct BHECommandErrorPayload: Decodable, Hashable {
    let title: String
    let explanation: String
    let suggestion: String?
    let technicalDetails: String?
    let relatedEntryID: String?
    let safeToRetry: Bool
    let originalISOModified: Bool
    let patchedCopyWritten: Bool
}

struct BHEBackendVersion: Decodable, Hashable {
    let protocolVersion: Int
    let backendVersion: String
    let readOnly: Bool
    let commands: [String]
}

struct BHEBackendHealth: Decodable, Hashable {
    let pythonExecutable: String
    let pythonVersion: String
    let dependencies: [BHEBackendDependency]
    let bchunk: BHEBackendToolStatus

    var missingRequiredDependencies: [BHEBackendDependency] {
        dependencies.filter { $0.requiredForBHE && !$0.available }
    }
}

struct BHEBackendDependency: Decodable, Identifiable, Hashable {
    let name: String
    let module: String
    let available: Bool
    let requiredForBHE: Bool

    var id: String { module }
}

struct BHEBackendToolStatus: Decodable, Hashable {
    let available: Bool
    let path: String?
}

struct BHESupportedTypes: Decodable, Hashable {
    let sourceTypes: [BHESupportedSourceType]
    let entryTypes: [BHESupportedEntryType]
    let writeSupport: BHEWriteSupport
}

struct BHESupportedSourceType: Decodable, Hashable {
    let `extension`: String
    let role: String
    let support: String
    let notes: String
}

struct BHESupportedEntryType: Decodable, Hashable {
    let kind: String
    let format: String
    let operations: [String]
    let readOnly: Bool
    let writable: Bool
}

struct BHEWriteSupport: Decodable, Hashable {
    let originalISOModification: Bool
    let patchedCopyWriting: Bool
    let replacementValidation: Bool
}

private struct BHECommandErrorEnvelope: Decodable {
    let protocolVersion: Int?
    let backendVersion: String?
    let status: String?
    let error: BHECommandErrorPayload
}

private struct BHECommandSuccessEnvelope<Payload: Decodable>: Decodable {
    let protocolVersion: Int
    let backendVersion: String
    let status: String
    let data: Payload
}

struct ProcessBHEBackendClient: BHEBackendClient {
    private let supportedProtocolVersion = 1

    var pythonExecutable: URL?
    var commandEntrypoint: URL?

    func version() async throws -> BHEBackendVersion {
        let data = try await runPythonCommand(["version"])
        do {
            return try decodeEnvelope(BHEBackendVersion.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func healthCheck() async throws -> BHEBackendHealth {
        let data = try await runPythonCommand(["health-check"])
        do {
            return try decodeEnvelope(BHEBackendHealth.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func listSupportedTypes() async throws -> BHESupportedTypes {
        let data = try await runPythonCommand(["list-supported-types"])
        do {
            return try decodeEnvelope(BHESupportedTypes.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func scanISO(at url: URL) async throws -> BHEScanResult {
        let data = try await runPythonCommand(["scan-iso", url.path])
        do {
            return try decodeEnvelope(BHEScanResult.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func scanDiscRoot(at url: URL) async throws -> BHEScanResult {
        let data = try await runPythonCommand(["scan-disc-root", url.path])
        do {
            return try decodeEnvelope(BHEScanResult.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func scanEGameDiscRoot(at url: URL) async throws -> BHEScanResult {
        let data = try await runPythonCommand(["scan-egame-disc-root", url.path])
        do {
            return try decodeEnvelope(BHEScanResult.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func previewTexture(in isoURL: URL, entryID: BHEEntry.ID, outputURL: URL) async throws -> BHETexturePreviewResult {
        let data = try await runPythonCommand([
            "preview-texture",
            isoURL.path,
            entryID,
            "--output",
            outputURL.path
        ])
        do {
            return try decodeEnvelope(BHETexturePreviewResult.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func previewTexture(inDiscRoot rootURL: URL, entryID: BHEEntry.ID, outputURL: URL) async throws -> BHETexturePreviewResult {
        let data = try await runPythonCommand([
            "preview-texture-disc-root",
            rootURL.path,
            entryID,
            "--output",
            outputURL.path
        ])
        do {
            return try decodeEnvelope(BHETexturePreviewResult.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func extractTexture(from isoURL: URL, entryID: BHEEntry.ID, outputURL: URL) async throws -> BHETextureExtractionResult {
        let data = try await runPythonCommand([
            "extract-texture",
            isoURL.path,
            entryID,
            "--output",
            outputURL.path
        ])
        do {
            return try decodeEnvelope(BHETextureExtractionResult.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    func extractTexture(fromDiscRoot rootURL: URL, entryID: BHEEntry.ID, outputURL: URL) async throws -> BHETextureExtractionResult {
        let data = try await runPythonCommand([
            "extract-texture-disc-root",
            rootURL.path,
            entryID,
            "--output",
            outputURL.path
        ])
        do {
            return try decodeEnvelope(BHETextureExtractionResult.self, from: data)
        } catch {
            throw mapDecodeError(error)
        }
    }

    private func runPythonCommand(_ arguments: [String]) async throws -> Data {
        guard let entrypoint = resolvedEntrypoint else {
            throw BHEBackendError.commandUnavailable("Expected backend/choroq/bhe/bhe_json.py in the app bundle resources.")
        }

        let process = Process()
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        let stdoutBuffer = ProcessOutputBuffer()
        let stderrBuffer = ProcessOutputBuffer()
        let resolvedPythonExecutable = resolvedPythonExecutable
        let useEnvironmentPython = resolvedPythonExecutable == nil

        process.executableURL = resolvedPythonExecutable ?? URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = (useEnvironmentPython ? ["python3"] : []) + [entrypoint.path] + arguments
        process.currentDirectoryURL = repositoryRoot(for: entrypoint)
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        stdoutPipe.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty {
                stdoutBuffer.append(data)
            }
        }
        stderrPipe.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty {
                stderrBuffer.append(data)
            }
        }

        return try await withCheckedThrowingContinuation { continuation in
            process.terminationHandler = { completedProcess in
                stdoutPipe.fileHandleForReading.readabilityHandler = nil
                stderrPipe.fileHandleForReading.readabilityHandler = nil

                stdoutBuffer.append(stdoutPipe.fileHandleForReading.readDataToEndOfFile())
                stderrBuffer.append(stderrPipe.fileHandleForReading.readDataToEndOfFile())

                let stdout = stdoutBuffer.snapshot()
                let stderr = stderrBuffer.snapshot()
                if completedProcess.terminationStatus == 0 {
                    continuation.resume(returning: stdout)
                } else {
                    continuation.resume(throwing: commandFailure(stdout: stdout, stderr: stderr))
                }
            }

            do {
                try process.run()
            } catch {
                stdoutPipe.fileHandleForReading.readabilityHandler = nil
                stderrPipe.fileHandleForReading.readabilityHandler = nil
                continuation.resume(throwing: error)
            }
        }
    }

    private func decodeEnvelope<Payload: Decodable>(_ payloadType: Payload.Type, from data: Data) throws -> Payload {
        let envelope = try JSONDecoder().decode(BHECommandSuccessEnvelope<Payload>.self, from: data)
        guard envelope.status == "ok" else {
            throw BHEBackendError.invalidResponse("Expected status 'ok', got '\(envelope.status)'.")
        }
        guard envelope.protocolVersion <= supportedProtocolVersion else {
            throw BHEBackendError.incompatibleProtocol(envelope.protocolVersion, backendVersion: envelope.backendVersion)
        }
        return envelope.data
    }

    private func mapDecodeError(_ error: Error) -> Error {
        if case BHEBackendError.incompatibleProtocol = error {
            return error
        }
        if case BHEBackendError.invalidResponse = error {
            return error
        }
        return BHEBackendError.invalidResponse(error.localizedDescription)
    }

    private var resolvedEntrypoint: URL? {
        let bundledEntrypoint = Bundle.main.resourceURL?
            .appendingPathComponent("backend/choroq/bhe/bhe_json.py")
        if let bundledEntrypoint, FileManager.default.fileExists(atPath: bundledEntrypoint.path) {
            return bundledEntrypoint
        }

        if let commandEntrypoint, FileManager.default.fileExists(atPath: commandEntrypoint.path) {
            return commandEntrypoint
        }

        if let environmentPath = ProcessInfo.processInfo.environment["CHOROQ_BHE_BRIDGE"],
           !environmentPath.isEmpty {
            let environmentEntrypoint = URL(fileURLWithPath: environmentPath)
            if FileManager.default.fileExists(atPath: environmentEntrypoint.path) {
                return environmentEntrypoint
            }
        }

        guard !isRunningFromAppBundle else {
            return nil
        }

        let currentDirectory = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        let sourceCheckoutRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()

        let candidates = [
            bundledEntrypoint,
            currentDirectory.appendingPathComponent("choroq/bhe/bhe_json.py"),
            currentDirectory.deletingLastPathComponent().appendingPathComponent("choroq/bhe/bhe_json.py"),
            sourceCheckoutRoot.appendingPathComponent("choroq/bhe/bhe_json.py")
        ].compactMap { $0 }

        return candidates.first { FileManager.default.fileExists(atPath: $0.path) }
    }

    private var isRunningFromAppBundle: Bool {
        Bundle.main.bundleURL.pathExtension == "app"
    }

    private var resolvedPythonExecutable: URL? {
        if let pythonExecutable {
            return pythonExecutable
        }
        guard let environmentPath = ProcessInfo.processInfo.environment["CHOROQ_BHE_PYTHON"],
              !environmentPath.isEmpty else {
            return nil
        }
        return URL(fileURLWithPath: environmentPath)
    }

    private func repositoryRoot(for entrypoint: URL) -> URL {
        entrypoint
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    private nonisolated func commandFailure(stdout: Data, stderr: Data) -> Error {
        if let envelope = try? JSONDecoder().decode(BHECommandErrorEnvelope.self, from: stdout) {
            return BHEBackendError.commandFailed(envelope.error)
        }

        let stderrText = String(data: stderr, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
        let stdoutText = String(data: stdout, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
        let details = [stderrText, stdoutText]
            .compactMap { value in
                guard let value, !value.isEmpty else { return nil }
                return value
            }
            .joined(separator: "\n")

        return BHEBackendError.invalidResponse(details.isEmpty ? "No error details were returned." : details)
    }
}

private final class ProcessOutputBuffer: @unchecked Sendable {
    private let lock = NSLock()
    private var data = Data()

    func append(_ newData: Data) {
        guard !newData.isEmpty else {
            return
        }
        lock.lock()
        data.append(newData)
        lock.unlock()
    }

    func snapshot() -> Data {
        lock.lock()
        defer { lock.unlock() }
        return data
    }
}
