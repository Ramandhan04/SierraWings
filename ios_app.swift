import SwiftUI
import MapKit
import CoreLocation
import UserNotifications

// MARK: - Main App
@main
struct SierraWingsApp: App {
    @StateObject private var authManager = AuthManager()
    @StateObject private var locationManager = LocationManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .environmentObject(locationManager)
                .onAppear {
                    requestNotificationPermission()
                }
        }
    }
    
    private func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, error in
            if granted {
                print("Notification permission granted")
            }
        }
    }
}

// MARK: - Content View
struct ContentView: View {
    @EnvironmentObject var authManager: AuthManager
    
    var body: some View {
        Group {
            if authManager.isAuthenticated {
                MainTabView()
            } else {
                LoginView()
            }
        }
    }
}

// MARK: - Main Tab View
struct MainTabView: View {
    var body: some View {
        TabView {
            HomeView()
                .tabItem {
                    Image(systemName: "house.fill")
                    Text("Home")
                }
            
            DeliveryTrackingView()
                .tabItem {
                    Image(systemName: "location.fill")
                    Text("Track")
                }
            
            ClinicsView()
                .tabItem {
                    Image(systemName: "cross.case.fill")
                    Text("Clinics")
                }
            
            ProfileView()
                .tabItem {
                    Image(systemName: "person.fill")
                    Text("Profile")
                }
        }
        .accentColor(.blue)
    }
}

// MARK: - Home View
struct HomeView: View {
    @State private var showingEmergencyRequest = false
    @EnvironmentObject var locationManager: LocationManager
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Header
                    VStack(spacing: 12) {
                        Image("sierrawings_logo")
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .frame(width: 80, height: 80)
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                        
                        Text("SierraWings")
                            .font(.largeTitle)
                            .fontWeight(.bold)
                            .foregroundColor(.primary)
                        
                        Text("Emergency Medical Drone Delivery")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding()
                    .background(
                        LinearGradient(
                            gradient: Gradient(colors: [Color.blue.opacity(0.1), Color.blue.opacity(0.05)]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .cornerRadius(20)
                    
                    // Quick Actions Grid
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Quick Actions")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .padding(.horizontal)
                        
                        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 16), count: 2), spacing: 16) {
                            QuickActionCard(
                                title: "Emergency\nDelivery",
                                icon: "cross.case.circle.fill",
                                color: .red,
                                action: { showingEmergencyRequest = true }
                            )
                            
                            QuickActionCard(
                                title: "Track\nDelivery",
                                icon: "location.circle.fill",
                                color: .blue,
                                action: { /* Navigate to tracking */ }
                            )
                            
                            QuickActionCard(
                                title: "Find\nClinics",
                                icon: "mappin.circle.fill",
                                color: .green,
                                action: { /* Navigate to clinics */ }
                            )
                            
                            QuickActionCard(
                                title: "My\nProfile",
                                icon: "person.circle.fill",
                                color: .purple,
                                action: { /* Navigate to profile */ }
                            )
                        }
                        .padding(.horizontal)
                    }
                    
                    // Recent Deliveries
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Recent Deliveries")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .padding(.horizontal)
                        
                        LazyVStack(spacing: 12) {
                            ForEach(mockRecentDeliveries) { delivery in
                                DeliveryCard(delivery: delivery)
                            }
                        }
                        .padding(.horizontal)
                    }
                    
                    // Emergency Contact
                    EmergencyContactCard()
                        .padding(.horizontal)
                    
                    // Footer
                    VStack(spacing: 4) {
                        Text("© 2025 SierraWings. All rights reserved.")
                        Text("Developed by Sahid R.M Dumbuya & Maada Lumeh")
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding()
                }
            }
            .navigationTitle("")
            .navigationBarHidden(true)
        }
        .sheet(isPresented: $showingEmergencyRequest) {
            EmergencyRequestView()
        }
    }
}

// MARK: - Quick Action Card
struct QuickActionCard: View {
    let title: String
    let icon: String
    let color: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 40))
                    .foregroundColor(.white)
                
                Text(title)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)
            }
            .frame(height: 120)
            .frame(maxWidth: .infinity)
            .background(color)
            .cornerRadius(16)
            .shadow(color: color.opacity(0.3), radius: 8, x: 0, y: 4)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// MARK: - Delivery Card
struct DeliveryCard: View {
    let delivery: Delivery
    
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(delivery.type)
                    .font(.headline)
                    .foregroundColor(.primary)
                
                Text(delivery.destination)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                Text(delivery.date)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            StatusBadge(status: delivery.status)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
}

// MARK: - Status Badge
struct StatusBadge: View {
    let status: DeliveryStatus
    
    var body: some View {
        Text(status.rawValue)
            .font(.caption)
            .fontWeight(.medium)
            .padding(.horizontal, 12)
            .padding(.vertical, 4)
            .background(status.color.opacity(0.2))
            .foregroundColor(status.color)
            .cornerRadius(8)
    }
}

// MARK: - Emergency Contact Card
struct EmergencyContactCard: View {
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 8) {
                Text("24/7 Emergency Support")
                    .font(.headline)
                    .foregroundColor(.white)
                
                Text("+232-XXX-XXXX")
                    .font(.subheadline)
                    .foregroundColor(.white.opacity(0.9))
            }
            
            Spacer()
            
            Button("CALL") {
                if let url = URL(string: "tel://+232XXXXXXX") {
                    UIApplication.shared.open(url)
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 8)
            .background(Color.white)
            .foregroundColor(.orange)
            .fontWeight(.bold)
            .cornerRadius(8)
        }
        .padding()
        .background(Color.orange)
        .cornerRadius(12)
        .shadow(color: .orange.opacity(0.3), radius: 8, x: 0, y: 4)
    }
}

// MARK: - Emergency Request View
struct EmergencyRequestView: View {
    @State private var selectedMedicationType = "Prescription Medication"
    @State private var deliveryAddress = ""
    @State private var specialInstructions = ""
    @State private var urgencyLevel = "High"
    @Environment(\.presentationMode) var presentationMode
    
    let medicationTypes = ["Prescription Medication", "Emergency Supplies", "Medical Equipment", "Vaccines"]
    let urgencyLevels = ["Low", "Normal", "High", "Emergency"]
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Medical Request Details")) {
                    Picker("Medication Type", selection: $selectedMedicationType) {
                        ForEach(medicationTypes, id: \.self) { type in
                            Text(type).tag(type)
                        }
                    }
                    
                    Picker("Urgency Level", selection: $urgencyLevel) {
                        ForEach(urgencyLevels, id: \.self) { level in
                            Text(level).tag(level)
                        }
                    }
                }
                
                Section(header: Text("Delivery Information")) {
                    TextField("Delivery Address", text: $deliveryAddress)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                    
                    TextField("Special Instructions", text: $specialInstructions, axis: .vertical)
                        .lineLimit(3...6)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                }
                
                Section {
                    Button("Submit Emergency Request") {
                        submitEmergencyRequest()
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.red)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
            }
            .navigationTitle("Emergency Request")
            .navigationBarItems(
                leading: Button("Cancel") {
                    presentationMode.wrappedValue.dismiss()
                }
            )
        }
    }
    
    private func submitEmergencyRequest() {
        // Submit emergency request logic
        presentationMode.wrappedValue.dismiss()
    }
}

// MARK: - Login View
struct LoginView: View {
    @State private var email = ""
    @State private var password = ""
    @State private var showingRegistration = false
    @EnvironmentObject var authManager: AuthManager
    
    var body: some View {
        VStack(spacing: 24) {
            // Logo and Title
            VStack(spacing: 16) {
                Image("sierrawings_logo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 100, height: 100)
                    .clipShape(RoundedRectangle(cornerRadius: 20))
                
                Text("SierraWings")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                    .foregroundColor(.primary)
                
                Text("Emergency Medical Drone Delivery")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            // Login Form
            VStack(spacing: 16) {
                TextField("Email", text: $email)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .autocapitalization(.none)
                    .keyboardType(.emailAddress)
                
                SecureField("Password", text: $password)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                
                Button("Sign In") {
                    authManager.login(email: email, password: password)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
                
                Button("Create Account") {
                    showingRegistration = true
                }
                .foregroundColor(.blue)
            }
            .padding(.horizontal)
            
            Spacer()
        }
        .padding()
        .sheet(isPresented: $showingRegistration) {
            RegistrationView()
        }
    }
}

// MARK: - Data Models
struct Delivery: Identifiable {
    let id = UUID()
    let type: String
    let destination: String
    let date: String
    let status: DeliveryStatus
}

enum DeliveryStatus: String, CaseIterable {
    case pending = "Pending"
    case inProgress = "In Progress"
    case delivered = "Delivered"
    case cancelled = "Cancelled"
    
    var color: Color {
        switch self {
        case .pending: return .orange
        case .inProgress: return .blue
        case .delivered: return .green
        case .cancelled: return .red
        }
    }
}

// MARK: - Managers
class AuthManager: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    
    func login(email: String, password: String) {
        // Implement login logic with SierraWings API
        // For demo purposes, simulate successful login
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            self.isAuthenticated = true
            self.currentUser = User(name: "John Doe", email: email, role: .patient)
        }
    }
    
    func logout() {
        isAuthenticated = false
        currentUser = nil
    }
}

class LocationManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    private let locationManager = CLLocationManager()
    @Published var location: CLLocation?
    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined
    
    override init() {
        super.init()
        locationManager.delegate = self
        locationManager.requestWhenInUseAuthorization()
    }
    
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authorizationStatus = manager.authorizationStatus
        if authorizationStatus == .authorizedWhenInUse || authorizationStatus == .authorizedAlways {
            locationManager.startUpdatingLocation()
        }
    }
    
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        location = locations.last
    }
}

struct User {
    let name: String
    let email: String
    let role: UserRole
}

enum UserRole {
    case patient
    case clinic
    case admin
}

// MARK: - Mock Data
let mockRecentDeliveries = [
    Delivery(type: "Emergency Medication", destination: "Freetown Central", date: "2025-06-13", status: .delivered),
    Delivery(type: "Medical Supplies", destination: "Bo District", date: "2025-06-12", status: .inProgress),
    Delivery(type: "Prescription Drugs", destination: "Kenema Hospital", date: "2025-06-11", status: .pending)
]

// MARK: - Additional Views (Stubs)
struct DeliveryTrackingView: View {
    var body: some View {
        Text("Delivery Tracking")
            .navigationTitle("Track Delivery")
    }
}

struct ClinicsView: View {
    var body: some View {
        Text("Nearby Clinics")
            .navigationTitle("Clinics")
    }
}

struct ProfileView: View {
    @EnvironmentObject var authManager: AuthManager
    
    var body: some View {
        VStack {
            Text("User Profile")
                .navigationTitle("Profile")
            
            Button("Logout") {
                authManager.logout()
            }
            .padding()
            .background(Color.red)
            .foregroundColor(.white)
            .cornerRadius(8)
        }
    }
}

struct RegistrationView: View {
    @Environment(\.presentationMode) var presentationMode
    
    var body: some View {
        Text("Registration Form")
            .navigationTitle("Create Account")
            .navigationBarItems(
                leading: Button("Cancel") {
                    presentationMode.wrappedValue.dismiss()
                }
            )
    }
}

/*
ADDITIONAL iOS FILES NEEDED:

1. Info.plist permissions:
<key>NSLocationWhenInUseUsageDescription</key>
<string>SierraWings needs location access to provide accurate delivery services and find nearby clinics.</string>

<key>NSCameraUsageDescription</key>
<string>SierraWings needs camera access to scan QR codes and take photos for delivery verification.</string>

<key>NSPhoneCallUsageDescription</key>
<string>SierraWings needs phone access to make emergency calls for medical assistance.</string>

2. Package Dependencies (Package.swift):
- Alamofire for networking
- KeychainAccess for secure storage
- MapKit for location services
- UserNotifications for push notifications

3. Additional Features to Implement:
- WebKit integration for SierraWings web platform
- Push notification handling
- Biometric authentication (Face ID/Touch ID)
- Secure keychain storage for auth tokens
- Payment gateway integration (Mobile Money APIs)
- Real-time drone tracking with MapKit
- Emergency calling functionality
- QR code scanning for delivery verification

4. Build Configuration:
- Target iOS 14.0+
- Swift 5.0+
- Xcode 13.0+
- Code signing for App Store distribution
- App Transport Security configuration for HTTPS

5. App Store Requirements:
- App icons (all required sizes)
- Launch screen storyboard
- Privacy policy URL
- App description and keywords
- Screenshots for all device sizes
- App Store review guidelines compliance
*/