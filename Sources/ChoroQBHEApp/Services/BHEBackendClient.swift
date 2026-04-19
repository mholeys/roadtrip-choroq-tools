import Foundation

@MainActor
protocol BHEBackendClient {
    func scanISO(at url: URL) async throws -> BHEScanResult
    func loadSampleSession() async throws -> BHEScanResult
}

enum BHEBackendError: LocalizedError {
    case bridgeUnavailable

    var errorDescription: String? {
        switch self {
        case .bridgeUnavailable:
            "The Python JSON bridge has not been wired yet."
        }
    }
}

struct ProcessBHEBackendClient: BHEBackendClient {
    var pythonExecutable: URL
    var bridgeScript: URL

    func scanISO(at url: URL) async throws -> BHEScanResult {
        throw BHEBackendError.bridgeUnavailable
    }

    func loadSampleSession() async throws -> BHEScanResult {
        try await MockBHEBackendClient().loadSampleSession()
    }
}

struct MockBHEBackendClient: BHEBackendClient {
    func scanISO(at url: URL) async throws -> BHEScanResult {
        let sample = try await loadSampleSession()
        return BHEScanResult(
            iso: BHEISOSummary(
                id: sample.iso.id,
                isoName: url.lastPathComponent,
                gameTitle: sample.iso.gameTitle,
                variant: sample.iso.variant,
                cpkCount: sample.iso.cpkCount,
                textureCount: sample.iso.textureCount
            ),
            entries: sample.entries
        )
    }

    func loadSampleSession() async throws -> BHEScanResult {
        BHEScanResult(
            iso: BHEISOSummary(
                id: "SLUS_209.30",
                isoName: "CHOROQ_HG4.iso",
                gameTitle: "Choro-Q HG4",
                variant: "US",
                cpkCount: 5,
                textureCount: 9
            ),
            entries: [
                BHEEntry(
                    id: "3DMAP.CPK:14:kan001",
                    cpkName: "3DMAP.CPK",
                    name: "kan001",
                    kind: .texture,
                    format: "4",
                    width: 128,
                    height: 64,
                    paletteSize: 16,
                    sizeBytes: 4112,
                    offsetBytes: 12_345_678,
                    sector: 6028,
                    support: .supported,
                    canExtract: true,
                    canReplace: true
                ),
                BHEEntry(
                    id: "3DMAP.CPK:14:Man001",
                    cpkName: "3DMAP.CPK",
                    name: "Man001",
                    kind: .texture,
                    format: "4",
                    width: 64,
                    height: 32,
                    paletteSize: 16,
                    sizeBytes: 1040,
                    offsetBytes: 12_349_790,
                    sector: 6030,
                    support: .supported,
                    canExtract: true,
                    canReplace: true
                ),
                BHEEntry(
                    id: "3DMAP.CPK:22:LZS",
                    cpkName: "3DMAP.CPK",
                    name: "[22] Compressed data",
                    kind: .lzs,
                    format: "LZS",
                    width: nil,
                    height: nil,
                    paletteSize: nil,
                    sizeBytes: 98_304,
                    offsetBytes: 13_631_488,
                    sector: 6656,
                    support: .compressed,
                    canExtract: false,
                    canReplace: false
                ),
                BHEEntry(
                    id: "BODY.CPK:3:cart_0",
                    cpkName: "BODY.CPK",
                    name: "cart_0",
                    kind: .texture,
                    format: "8",
                    width: 256,
                    height: 128,
                    paletteSize: 256,
                    sizeBytes: 33_808,
                    offsetBytes: 8_704_016,
                    sector: 4249,
                    support: .supported,
                    canExtract: true,
                    canReplace: true
                ),
                BHEEntry(
                    id: "BODY.CPK:4:PBL",
                    cpkName: "BODY.CPK",
                    name: "[4] PBL",
                    kind: .model,
                    format: "PBL",
                    width: nil,
                    height: nil,
                    paletteSize: nil,
                    sizeBytes: 76_192,
                    offsetBytes: 8_792_064,
                    sector: 4293,
                    support: .readOnly,
                    canExtract: false,
                    canReplace: false
                ),
                BHEEntry(
                    id: "SIGN.CPK:10:kan100",
                    cpkName: "SIGN.CPK",
                    name: "kan100",
                    kind: .texture,
                    format: "8",
                    width: 128,
                    height: 128,
                    paletteSize: 256,
                    sizeBytes: 17_424,
                    offsetBytes: 18_116_608,
                    sector: 8846,
                    support: .risky,
                    canExtract: true,
                    canReplace: false
                )
            ]
        )
    }
}
