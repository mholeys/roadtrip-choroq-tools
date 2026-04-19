// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "RoadtripChoroQTools",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "ChoroQBHEApp", targets: ["ChoroQBHEApp"])
    ],
    targets: [
        .executableTarget(name: "ChoroQBHEApp")
    ]
)
