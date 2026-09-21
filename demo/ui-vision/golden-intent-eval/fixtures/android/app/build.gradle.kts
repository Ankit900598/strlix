plugins { id("com.android.application") }

android {
    namespace = "com.zevi.goldenfixture"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.zevi.goldenfixture"
        minSdk = 30
        targetSdk = 34
        versionCode = 1
        versionName = "1.0-fixture"
    }
    buildTypes {
        release { isMinifyEnabled = false }
        debug { isDebuggable = true }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
