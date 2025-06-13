from app import db
from datetime import datetime
from sqlalchemy import Text, Boolean

class PaymentTransaction(db.Model):
    """Payment transactions tracking for admin dashboard"""
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey('mission.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Transaction Details
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # africanmoney, orangemoney, qmoney, card
    payment_provider = db.Column(db.String(50))  # Provider specific details
    
    # Amount Breakdown (in New Leones - NLE)
    total_amount = db.Column(db.Float, nullable=False)
    base_cost = db.Column(db.Float, default=30.0)  # Base drone delivery cost
    medical_item_cost = db.Column(db.Float, default=0.0)  # Cost based on medical item type
    weight_cost = db.Column(db.Float, default=0.0)  # Weight-based additional cost
    
    # Admin Fee Management
    admin_percentage = db.Column(db.Float, default=15.0)  # Admin fee percentage (15%)
    admin_fee_amount = db.Column(db.Float, nullable=False)  # Calculated admin fee
    net_amount = db.Column(db.Float, nullable=False)  # Amount after admin fee
    
    # Transaction Status
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_date = db.Column(db.DateTime)
    
    # Provider Response Data
    provider_transaction_id = db.Column(db.String(200))
    provider_response = db.Column(Text)  # JSON response from payment provider
    
    # Withdrawal Information
    is_withdrawn = db.Column(Boolean, default=False)
    withdrawal_date = db.Column(db.DateTime)
    withdrawal_method = db.Column(db.String(50))  # solana, bank_transfer, mobile_money
    withdrawal_address = db.Column(db.String(200))  # Solana wallet address or account details
    withdrawal_transaction_id = db.Column(db.String(200))
    
    # Relationships
    mission = db.relationship('Mission', backref='payment_transaction')
    user = db.relationship('User', backref='payment_transactions')
    
    def __repr__(self):
        return f'<PaymentTransaction {self.transaction_id}: {self.total_amount} NLE>'
    
    def calculate_costs(self, payload_weight, medical_item_type):
        """Calculate total cost based on weight and medical item type"""
        
        # Medical item type rates (in NLE)
        medical_rates = {
            'medications': 5.0,
            'vaccines': 15.0,
            'blood_products': 25.0,
            'medical_supplies': 8.0,
            'emergency_supplies': 20.0,
            'laboratory_samples': 12.0,
            'surgical_instruments': 18.0,
            'diagnostic_equipment': 30.0,
            'first_aid_supplies': 3.0,
            'prescription_drugs': 10.0
        }
        
        # Base cost (fixed)
        self.base_cost = 30.0
        
        # Medical item cost based on type
        self.medical_item_cost = medical_rates.get(medical_item_type.lower(), 5.0)
        
        # Weight-based cost calculation (per KG above 1KG)
        if payload_weight > 1.0:
            extra_weight = payload_weight - 1.0
            self.weight_cost = extra_weight * 2.0  # 2 NLE per additional KG
        else:
            self.weight_cost = 0.0
        
        # Calculate total before admin fee
        subtotal = self.base_cost + self.medical_item_cost + self.weight_cost
        
        # Calculate admin fee (15% of subtotal)
        self.admin_fee_amount = subtotal * (self.admin_percentage / 100)
        
        # Total amount including admin fee
        self.total_amount = subtotal + self.admin_fee_amount
        
        # Net amount for clinic (subtotal without admin fee)
        self.net_amount = subtotal
        
        return self.total_amount

class AdminWithdrawal(db.Model):
    """Track admin fee withdrawals"""
    __tablename__ = 'admin_withdrawals'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Withdrawal Details
    withdrawal_amount = db.Column(db.Float, nullable=False)
    withdrawal_method = db.Column(db.String(50), nullable=False)  # solana, bank_transfer
    withdrawal_address = db.Column(db.String(200), nullable=False)  # Wallet address or account
    
    # Transaction Information
    transaction_id = db.Column(db.String(200))
    transaction_hash = db.Column(db.String(200))  # For blockchain transactions
    
    # Status and Dates
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    requested_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)
    
    # Fees included in this withdrawal
    payment_transaction_ids = db.Column(Text)  # JSON array of included payment transaction IDs
    
    # Notes
    notes = db.Column(Text)
    
    def __repr__(self):
        return f'<AdminWithdrawal {self.withdrawal_amount} NLE via {self.withdrawal_method}>'

class MedicalItemPricing(db.Model):
    """Medical item pricing configuration"""
    __tablename__ = 'medical_item_pricing'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(100), unique=True, nullable=False)
    base_rate = db.Column(db.Float, nullable=False)  # Rate in NLE
    description = db.Column(db.String(200))
    
    # Weight considerations
    weight_sensitive = db.Column(Boolean, default=True)
    max_recommended_weight = db.Column(db.Float, default=10.0)  # in KG
    
    # Status
    is_active = db.Column(Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MedicalItemPricing {self.item_type}: {self.base_rate} NLE>'