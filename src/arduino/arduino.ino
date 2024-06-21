int inPin = 7;
int val = 0;
int pulseCount = 0;
bool up = false;
String recievedMessage = "";
String MessageBuffer = "";

void setup(){
  pinMode(inPin, INPUT);
  Serial.begin(9600);
  Serial1.begin(9600);
}

void loop(){
  val = digitalRead(inPin);
  if (up == false && val == HIGH){
    up=true;
  }
  else if (up == true && val == LOW){
    up = false;
    pulseCount += 1;
  }
  
  while (Serial1.available() > 0) {
    char receivedChar = Serial1.read();
    if (receivedChar == '\n') {
      MessageBuffer = recievedMessage;  // Print the received message in the Serial monitor
      recievedMessage = "";  // Reset the received message
      Serial.println(MessageBuffer);
    } else {
      recievedMessage += receivedChar;  // Append characters to the received message
    }
  }

  Serial.println(pulseCount);
  //Serial.println(MessageBuffer);
  if(Serial.available()){
        String serial_command = Serial.readStringUntil('\n');
        if (serial_command == "reset"){
          pulseCount = 0;
        }
        else {
          Serial1.println(serial_command);
        }
        }
}
