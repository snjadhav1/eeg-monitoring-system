#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// --------- USER CONFIG ---------
#define EEG_PIN A0             // ADC pin connected to BioAmp EXG Pill OUT
#define SAMPLE_RATE 250        // Hz (EEG standard safe sampling rate)
#define SAMPLES_PER_SECOND 250 // Collect 250 samples = 1 second
#define WIFI_SSID "OPPO F17"
#define WIFI_PASS "9876543210"
#define FLASK_SERVER_URL "https://eeg-monitoring-system.onrender.com/upload"
// --------------------------------

float samples[SAMPLES_PER_SECOND];
int sampleIndex = 0;
String deviceMAC = "";  // Store MAC address

// ✅ WiFi Connect & Auto-Reconnect
void connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;  // already connected
 
  WiFi.disconnect(true);       // reset old connections
  delay(500);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
 
  Serial.print("🔌 Connecting to WiFi");
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) {
    delay(500);
    Serial.print(".");
    retries++;
  }
 
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected!");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n⚠️ WiFi not connected. Running in Serial-only mode.");
  }
}

void setup() {
  Serial.begin(115200);
  delay(2000);
 
  // Initialize WiFi to get MAC (doesn't connect yet)
  WiFi.mode(WIFI_STA);
  deviceMAC = WiFi.macAddress();
 
  Serial.println("=============================");
  Serial.println("🚀 EEG Monitoring System");
  Serial.println("📡 Target: Render Deployment");
  Serial.print("📱 Device MAC: ");
  Serial.println(deviceMAC);
  Serial.print("🌐 Server URL: ");
  Serial.println(FLASK_SERVER_URL);
  Serial.println("=============================");
 
  connectToWiFi();            // auto-connect on boot
  analogReadResolution(12);   // 12-bit ADC (0–4095)
}

void loop() {
  // --- WiFi Auto-Reconnect ---
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ Lost WiFi! Reconnecting...");
    connectToWiFi();
  }
 
  unsigned long startMicros = micros();
 
  // --- Read BioAmp signal ---
  int raw = analogRead(EEG_PIN);
  samples[sampleIndex++] = raw;
 
  // Print every 50th sample to Serial (reduce spam)
  if (sampleIndex % 50 == 0) {
    Serial.print("Raw: ");
    Serial.println(raw);
  }
 
  // --- When 1 second of data collected (250 samples) ---
  if (sampleIndex >= SAMPLES_PER_SECOND) {
    // Calculate average
    float sum = 0;
    for (int i = 0; i < SAMPLES_PER_SECOND; i++) {
      sum += samples[i];
    }
    float average = sum / SAMPLES_PER_SECOND;
   
    // Check signal quality
    checkSignalQuality();
   
    // Send single averaged value with MAC
    sendAverageToFlask(average);
   
    // Reset for next second
    sampleIndex = 0;
  }
 
  // --- Timing control ---
  unsigned long elapsed = micros() - startMicros;
  unsigned long waitTime = (1000000UL / SAMPLE_RATE);
  if (elapsed < waitTime) {
    delayMicroseconds(waitTime - elapsed);
  }
}

// ✅ Quality Check
void checkSignalQuality() {
  float mean = 0, variance = 0;
 
  for (int i = 0; i < SAMPLES_PER_SECOND; i++) mean += samples[i];
  mean /= SAMPLES_PER_SECOND;
 
  for (int i = 0; i < SAMPLES_PER_SECOND; i++) variance += pow(samples[i] - mean, 2);
  float stddev = sqrt(variance / SAMPLES_PER_SECOND);
 
  if (mean < 500 || mean > 3500) {
    Serial.println("⚠️ BAD QUALITY: Signal Saturated / Loose Contact");
  } else if (stddev < 2) {
    Serial.println("⚠️ BAD QUALITY: Flatline (check electrodes)");
  } else if (stddev > 800) {
    Serial.println("⚠️ BAD QUALITY: High Noise / Movement Artifact");
  } else {
    Serial.println("✅ GOOD QUALITY: Signal Clean");
  }
}

// ✅ POST single average value with MAC to Flask (HTTPS)
void sendAverageToFlask(float avgValue) {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClientSecure client;
    client.setInsecure();  // Skip SSL certificate validation (for testing)
    
    HTTPClient http;
    http.begin(client, FLASK_SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000);  // 10 second timeout
    
    // Send MAC address + average value as JSON
    String json = "{\"mac\":\"" + deviceMAC + "\",\"average\":" + String(avgValue, 2) + "}";
    
    Serial.println("\n📤 ===== SENDING TO RENDER =====");
    Serial.print("MAC: ");
    Serial.println(deviceMAC);
    Serial.print("Average: ");
    Serial.println(avgValue);
    Serial.print("URL: ");
    Serial.println(FLASK_SERVER_URL);
    
    int httpResponseCode = http.POST(json);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.print("✅ [POST] Success: HTTP ");
      Serial.println(httpResponseCode);
      Serial.print("Response: ");
      Serial.println(response);
    } else {
      Serial.print("❌ [POST] Failed: ");
      Serial.println(http.errorToString(httpResponseCode).c_str());
      Serial.println("💡 Tip: Check if Render is awake (free tier sleeps after 15min)");
    }
    Serial.println("================================\n");
    
    http.end();
  } else {
    Serial.println("⚠️ [WARN] WiFi not connected, skipped POST.");
  }
}
