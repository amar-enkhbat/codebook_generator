const int ledPins[] = {0, 1, 2, 3, 4, 5, 6, 7};  // LED pins

void setup() {
    Serial.begin(115200);  // Start serial communication
    for (int i = 0; i < 8; i++) {
        pinMode(ledPins[i], OUTPUT);
    }
}

void loop() {
    if (Serial.available()) {
        String data = Serial.readStringUntil('\n');  // Read incoming data
        int values[8];
        int index = 0;

        char *ptr = strtok((char*)data.c_str(), ",");
        while (ptr != NULL && index < 8) {
            values[index++] = constrain(atoi(ptr), 0, 255);
            ptr = strtok(NULL, ",");
        }

        if (index == 8) {  // Ensure all 8 values are received
            for (int i = 0; i < 8; i++) {
                if (values[i] > 0) {  // If the value is greater than 127, turn LED on
                    digitalWrite(ledPins[i], HIGH);  // LED ON
                } else {  // Otherwise, turn LED off
                    digitalWrite(ledPins[i], LOW);  // LED OFF
                }
            }
        }
    }
}

// void loop() {
//     for (int i = 0; i < 8; i++) {
//         // analogWrite(ledPins[i], 255);  // Update LED brightness
//         digitalWrite(ledPins[i], HIGH);  // Update LED brightness
//     }
// }