// android/settings.gradle.kts (Flutter scaffold standard).
// Loads Flutter Gradle plugin via local flutter SDK; defines pluginManagement
// and dependencyResolutionManagement.

pluginManagement {
    val flutterSdkPath: String = run {
        val properties = java.util.Properties()
        file("../flutter_sdk_path.properties").inputStream().use { properties.load(it) ***REMOVED***
        properties.getProperty("flutter.sdk")
    ***REMOVED***

    includeBuild("$flutterSdkPath/packages/flutter_tools/gradle")

    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    ***REMOVED***
***REMOVED***

plugins {
    id("dev.flutter.flutter-plugin-loader") version "1.0.0"
    id("com.android.application") version "8.1.4" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
***REMOVED***

include(":app")
