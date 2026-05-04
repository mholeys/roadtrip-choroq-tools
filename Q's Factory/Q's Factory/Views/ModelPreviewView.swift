import AppKit
import SceneKit
import SwiftUI

struct ScenePreviewView: View {
    let entry: BHEEntry
    let modelURL: URL?
    let manifest: BHEExportManifest?
    let previewState: AssetPreviewState
    let isLoading: Bool
    let failureMessage: String?
    let relinkReport: MaterialRelinkReport

    var body: some View {
        WorkshopSection(title: "Scene Preview", systemImage: "cube.transparent") {
            ZStack {
                if let modelURL {
                    if let scene = ScenePreviewController.loadScene(from: modelURL, manifest: manifest) {
                        SceneKitSceneView(scene: scene)
                            .frame(minHeight: 260)
                            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                            .overlay(alignment: .topLeading) {
                                PreviewBadge(text: badgeText, systemImage: badgeImage)
                                    .padding(10)
                            }
                    } else {
                        fallbackView(
                            title: "Scene preview failed",
                            body: "Q's Factory found \(modelURL.lastPathComponent), but SceneKit could not load this OBJ/MTL asset."
                        )
                    }
                } else {
                    fallbackView(
                        title: isLoading ? "Generating model preview..." : "Model preview unavailable",
                        body: failureMessage ?? "Export or preview a supported Road Trip / HG2 / HG3 car model to create native-previewable OBJ assets."
                    )
                }

                if isLoading {
                    ProgressView()
                        .controlSize(.large)
                        .padding(12)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
        }
        .accessibilityLabel("Model preview for \(entry.name)")
    }

    private var badgeText: String {
        switch previewState {
        case .ready:
            relinkReport.automaticTextureCount > 0 ? "Textured preview" : "Geometry only"
        case .partial:
            "Partial material preview"
        case .failed:
            "Decoder failed"
        case .unsupported:
            "Unsupported"
        case .preparing:
            "Preparing scene"
        case .idle:
            "Scene preview"
        }
    }

    private var badgeImage: String {
        switch previewState {
        case .ready:
            "checkmark.circle"
        case .partial:
            "circle.lefthalf.filled"
        case .failed:
            "xmark.octagon"
        case .unsupported:
            "nosign"
        case .preparing:
            "clock"
        case .idle:
            "cube.transparent"
        }
    }

    private func fallbackView(title: String, body: String) -> some View {
        VStack(spacing: 10) {
            Image(systemName: "cube.transparent")
                .font(.system(size: 36, weight: .regular))
                .foregroundStyle(QFactoryTheme.factoryBlue)
            Text(title)
                .font(.headline)
            Text(body)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, minHeight: 220)
        .padding(.vertical, 20)
    }
}

struct ModelPreviewView: View {
    let entry: BHEEntry
    let modelURL: URL?
    let isLoading: Bool
    let failureMessage: String?

    var body: some View {
        ScenePreviewView(
            entry: entry,
            modelURL: modelURL,
            manifest: nil,
            previewState: isLoading ? .preparing(stage: "Preparing scene...") : (failureMessage == nil ? .ready : .failed(message: failureMessage ?? "")),
            isLoading: isLoading,
            failureMessage: failureMessage,
            relinkReport: .empty
        )
    }
}

private struct PreviewBadge: View {
    let text: String
    let systemImage: String

    var body: some View {
        Label(text, systemImage: systemImage)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(.regularMaterial, in: .rect(cornerRadius: 8))
    }
}

private struct SceneKitSceneView: NSViewRepresentable {
    let scene: SCNScene

    func makeNSView(context: Context) -> SCNView {
        let view = SCNView()
        view.allowsCameraControl = true
        view.autoenablesDefaultLighting = true
        view.backgroundColor = .clear
        view.scene = scene
        view.pointOfView = scene.rootNode.childNode(withName: ScenePreviewController.cameraName, recursively: true)
        return view
    }

    func updateNSView(_ view: SCNView, context: Context) {
        view.scene = scene
        view.pointOfView = scene.rootNode.childNode(withName: ScenePreviewController.cameraName, recursively: true)
    }

    static func dismantleNSView(_ view: SCNView, coordinator: ()) {
        view.scene?.rootNode.childNodes.forEach { $0.removeFromParentNode() }
        view.scene = nil
        view.pointOfView = nil
    }
}

private enum ScenePreviewController {
    static let cameraName = "QFactoryModelPreviewCamera"

    static func loadScene(from url: URL, manifest: BHEExportManifest?) -> SCNScene? {
        guard FileManager.default.fileExists(atPath: url.path),
              let scene = try? SCNScene(url: url, options: [
                .assetDirectoryURLs: [url.deletingLastPathComponent()]
              ]) else {
            return nil
        }

        relinkMaterials(in: scene, relativeTo: url.deletingLastPathComponent(), manifest: manifest)
        SceneLightingRig.addCameraAndLight(to: scene)
        return scene
    }

    private static func relinkMaterials(in scene: SCNScene, relativeTo directory: URL, manifest: BHEExportManifest?) {
        let manifestTextureURLs = manifest?.files
            .filter { $0.kind == "texture" && $0.exists }
            .map { URL(fileURLWithPath: $0.path) } ?? []
        scene.rootNode.enumerateChildNodes { node, _ in
            guard let geometry = node.geometry else { return }
            for material in geometry.materials {
                if material.diffuse.contents == nil {
                    material.diffuse.contents = manifestTextureURLs.first ?? NSColor.controlAccentColor
                }
                for property in [material.diffuse, material.ambient, material.multiply] {
                    if let textureName = property.contents as? String {
                        let textureURL = directory.appendingPathComponent(textureName)
                        if FileManager.default.fileExists(atPath: textureURL.path) {
                            property.contents = textureURL
                        }
                    }
                }
                material.lightingModel = .physicallyBased
                material.isDoubleSided = true
            }
        }
    }
}

private enum SceneLightingRig {
    static func addCameraAndLight(to scene: SCNScene) {
        let bounds = scene.rootNode.boundingBox
        let minVector = bounds.min
        let maxVector = bounds.max
        let center = SCNVector3(
            (minVector.x + maxVector.x) * 0.5,
            (minVector.y + maxVector.y) * 0.5,
            (minVector.z + maxVector.z) * 0.5
        )
        let width = maxVector.x - minVector.x
        let height = maxVector.y - minVector.y
        let depth = maxVector.z - minVector.z
        let radius = max(CGFloat(1), max(width, max(height, depth)))

        let camera = SCNCamera()
        camera.zNear = 0.01
        camera.zFar = Double(radius * 20)

        let cameraNode = SCNNode()
        cameraNode.name = ScenePreviewController.cameraName
        cameraNode.camera = camera
        cameraNode.position = SCNVector3(center.x, center.y + radius * 0.35, center.z + radius * 2.4)
        cameraNode.look(at: center)
        scene.rootNode.addChildNode(cameraNode)

        let ambient = SCNLight()
        ambient.type = .ambient
        ambient.intensity = 240
        ambient.color = NSColor(white: 0.72, alpha: 1)

        let ambientNode = SCNNode()
        ambientNode.light = ambient
        scene.rootNode.addChildNode(ambientNode)

        let light = SCNLight()
        light.type = .directional
        light.intensity = 900

        let lightNode = SCNNode()
        lightNode.light = light
        lightNode.position = SCNVector3(center.x + radius, center.y + radius, center.z + radius * 1.5)
        lightNode.look(at: center)
        scene.rootNode.addChildNode(lightNode)

        let fill = SCNLight()
        fill.type = .omni
        fill.intensity = 180

        let fillNode = SCNNode()
        fillNode.light = fill
        fillNode.position = SCNVector3(center.x - radius, center.y + radius * 0.45, center.z - radius)
        scene.rootNode.addChildNode(fillNode)
    }
}
