plugins {
    id("com.android.application")
}

android {
    namespace = "com.zevi.agent"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.zevi.agent"
        minSdk = 30
        targetSdk = 34
        versionCode = 4
        versionName = "0.3.1-split"
        // Probe order (see PilotClient): Azure HTTPS primary, then localhost reverse / emulator gateway.
        // Keys never ship in the APK.
        buildConfigField("String", "ANDROID_API_PUBLIC_URL", "\"https://strlix-edge-gjfueaccgwg9gmfv.z02.azurefd.net/android\"")
        buildConfigField("String", "ANDROID_API_URL", "\"http://127.0.0.1:8788\"")
        buildConfigField("String", "ANDROID_API_EMULATOR_URL", "\"http://10.0.2.2:8788\"")
        buildConfigField("String", "PILOT_BASE_URL", "\"http://127.0.0.1:8787\"")
        buildConfigField("String", "PILOT_EMULATOR_URL", "\"http://10.0.2.2:8787\"")
        // Pass P seams only: no local model or assistant-role claim ships in this build.
        buildConfigField("boolean", "ON_DEVICE_MODEL_ENABLED", "false")
        buildConfigField("boolean", "ASSISTANT_ROLE_HOOKS_ENABLED", "false")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
        debug {
            isDebuggable = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.cardview:cardview:1.0.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
