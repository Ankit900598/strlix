plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

import java.util.Properties

android {
    namespace = "com.phonecodex.app"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.phonecodex.app"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        val localProps = Properties()
        val localFile = rootProject.file("local.properties")
        if (localFile.exists()) {
            localFile.inputStream().use { localProps.load(it) }
        }
        fun strlixProp(key: String, env: String, fallback: String): String {
            val raw = localProps.getProperty(key)
                ?: System.getenv(env)
                ?: fallback
            return raw.trim()
        }
        val backendUrl = strlixProp(
            "strlix.backendUrl",
            "STRLIX_BACKEND_URL",
            "http://127.0.0.1:8787"
        ).trimEnd('/')
        val backendSecret = strlixProp(
            "strlix.backendSecret",
            "STRLIX_BACKEND_APP_SECRET",
            ""
        )
        fun quoted(value: String): String =
            "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""
        buildConfigField("String", "BACKEND_BASE_URL", quoted(backendUrl))
        buildConfigField("String", "BACKEND_APP_SECRET", quoted(backendSecret))
    }

    buildTypes {
        release {
            optimization {
                enable = false
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.compose.material:material-icons-extended")
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    testImplementation(libs.junit)
    testImplementation("org.json:json:20240303")
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}