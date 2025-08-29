# Gradle Plugins DSL

## Rationale

The Gradle plugins DSL provides better performance, clearer dependencies, and improved IDE support compared to the legacy `apply plugin` syntax. It allows Gradle to optimize plugin loading and provides better build analysis capabilities.

## Before/After Examples

### Kotlin Plugin Migration

**Before:**
```gradle
apply plugin: 'kotlin-android'
```

**After:**
```gradle
plugins {
    id("org.jetbrains.kotlin.android")
}
```

### Multiple Plugins

**Before:**
```gradle
apply plugin: 'com.android.application'
apply plugin: 'kotlin-android'
```

**After:**
```gradle
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}