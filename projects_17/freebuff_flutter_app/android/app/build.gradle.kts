// App-level android/app/build.gradle.kts (Flutter scaffold standard).
// Configures Android tooling for the `app` module.

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("dev.flutter.flutter-gradle-plugin")
***REMOVED***

android {
    namespace = "com.freebuff.flutterapp"
    compileSdk = 34
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        isCoreLibraryDesugaringEnabled = true
    ***REMOVED***

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    ***REMOVED***

    sourceSets {
        getByName("main").java.srcDirs("src/main/kotlin")
    ***REMOVED***

    defaultConfig {
        applicationId = "com.freebuff.flutterapp"
        minSdk = 26         // Required by flutter_background_service + connectedDevice baseline.
        targetSdk = 34      // Required for foregroundServiceType=connectedDevice enforcement.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        multiDexEnabled = true
    ***REMOVED***

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("debug")
        ***REMOVED***
    ***REMOVED***
***REMOVED***

flutter {
    source = "../.."
***REMOVED***

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-process:2.7.0")
    implementation("androidx.lifecycle:lifecycle-service:2.7.0")
***REMOVED***
