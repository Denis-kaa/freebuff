// Project-level android/build.gradle.kts (Flutter scaffold standard).
// This file is consumed by Gradle at project evaluation; defines
// subproject plugins + Flutter tooling dependency version.

buildscript {
    repositories {
        google()
        mavenCentral()
    ***REMOVED***
    dependencies {
        classpath("com.android.tools.build:gradle:8.1.4")
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.22")
        classpath("com.google.devtools.ksp:com.google.devtools.ksp.gradle.plugin:1.9.22-1.0.17")
    ***REMOVED***
***REMOVED***

allprojects {
    repositories {
        google()
        mavenCentral()
    ***REMOVED***
***REMOVED***

val newBuildSystem: String by rootProject.extra
rootProject.extra["flutterRoot"***REMOVED*** = newBuildSystem
val flutterRoot: String = rootProject.extra["flutterRoot"***REMOVED*** as String

Task<Any>("clean").configure {
    dependsOn("flutterClean")
***REMOVED***

Task<Any>("assemble").configure {
    dependsOn("flutterAssemble${targetPlatform.name.capitalize()***REMOVED***")
***REMOVED***
