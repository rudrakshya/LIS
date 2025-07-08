#!/usr/bin/env python3
"""
Laboratory Information System (LIS) - Main Entry Point
A comprehensive system for laboratory management and medical equipment communication.
"""

import sys
import logging
from datetime import datetime, date
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Import our LIS components
from src.core.config import settings
from src.core.database import create_tables, get_session, db_manager
from src.core.exceptions import LISException
from src.models import Patient, TestOrder, Sample, TestResult, Equipment
from src.models import OrderStatus, SampleType, EquipmentType, CommunicationProtocol
from src.communication.hl7_handler import hl7_handler

# Set up logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format,
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
console = Console()


def display_welcome():
    """Display welcome message and system information"""
    
    welcome_text = Text()
    welcome_text.append("🏥 Laboratory Information System (LIS)\n", style="bold blue")
    welcome_text.append(f"Version: {settings.app_version}\n", style="green")
    welcome_text.append(f"Environment: {settings.environment}\n", style="yellow")
    welcome_text.append(f"Database: {settings.database_url}\n", style="cyan")
    
    panel = Panel(
        welcome_text,
        title="[bold]LIS System Status[/bold]",
        border_style="blue"
    )
    
    console.print(panel)


def initialize_database():
    """Initialize database and create tables"""
    try:
        console.print("\n[bold blue]Initializing Database...[/bold blue]")
        
        # Test database connection
        if db_manager.test_connection():
            console.print("✅ Database connection successful")
        else:
            console.print("❌ Database connection failed")
            return False
        
        # Create tables
        create_tables()
        console.print("✅ Database tables created/verified")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Database initialization failed: {str(e)}")
        return False


def create_sample_data():
    """Create sample data for demonstration"""
    try:
        console.print("\n[bold blue]Creating Sample Data...[/bold blue]")
        
        with get_session() as session:
            # Create sample patients
            patients = [
                Patient(
                    patient_id="P001",
                    first_name="John",
                    last_name="Doe",
                    date_of_birth=date(1980, 1, 15),
                    gender="M",
                    phone="555-0123",
                    email="john.doe@email.com"
                ),
                Patient(
                    patient_id="P002", 
                    first_name="Jane",
                    last_name="Smith",
                    date_of_birth=date(1975, 6, 22),
                    gender="F",
                    phone="555-0456",
                    email="jane.smith@email.com"
                )
            ]
            
            for patient in patients:
                # Check if patient already exists
                existing = session.query(Patient).filter_by(patient_id=patient.patient_id).first()
                if not existing:
                    session.add(patient)
                    console.print(f"✅ Created patient: {patient.full_name}")
            
            # Create sample equipment
            equipment = Equipment(
                equipment_id="CHEM001",
                name="Chemistry Analyzer Pro",
                manufacturer="MedDevice Inc",
                model="ChemPro-2000",
                equipment_type=EquipmentType.CHEMISTRY_ANALYZER,
                communication_protocol=CommunicationProtocol.HL7,
                ip_address="192.168.1.100",
                port=5000,
                supported_tests=["GLU", "BUN", "CREA", "ALT", "AST"],
                sample_types=["serum", "plasma"],
                location="Chemistry Lab"
            )
            
            # Check if equipment already exists
            existing_eq = session.query(Equipment).filter_by(equipment_id=equipment.equipment_id).first()
            if not existing_eq:
                session.add(equipment)
                console.print(f"✅ Created equipment: {equipment.name}")
            
            session.commit()
            console.print("✅ Sample data created successfully")
            
    except Exception as e:
        console.print(f"❌ Failed to create sample data: {str(e)}")


def display_system_status():
    """Display current system status"""
    try:
        console.print("\n[bold blue]System Status:[/bold blue]")
        
        with get_session() as session:
            # Count records
            patient_count = session.query(Patient).count()
            equipment_count = session.query(Equipment).count()
            
            # Create status table
            table = Table(title="Database Statistics")
            table.add_column("Entity", style="cyan", no_wrap=True)
            table.add_column("Count", style="magenta")
            table.add_column("Status", style="green")
            
            table.add_row("Patients", str(patient_count), "✅ Active")
            table.add_row("Equipment", str(equipment_count), "✅ Active")
            table.add_row("Database", "Connected", "✅ Healthy")
            table.add_row("HL7 Handler", "Initialized", "✅ Ready")
            
            console.print(table)
            
    except Exception as e:
        console.print(f"❌ Failed to get system status: {str(e)}")


def test_hl7_processing():
    """Test HL7 message processing"""
    try:
        console.print("\n[bold blue]Testing HL7 Message Processing...[/bold blue]")
        
        # Sample HL7 order message
        sample_hl7_message = """MSH|^~\\&|LIS|LAB|EMR|HOSPITAL|20231201120000||ORM^O01|12345|P|2.5
PID|1||P001||Doe^John||19800101|M|||123 Main St^^City^ST^12345||555-0123
ORC|NW|ORDER123|||||||20231201120000
OBR|1|ORDER123||GLU^Glucose|||20231201120000|||||||||Dr. Smith"""
        
        console.print("📨 Processing sample HL7 message...")
        console.print(f"Message preview: {sample_hl7_message[:80]}...")
        
        # Process the message
        response = hl7_handler.process_message(sample_hl7_message)
        
        # Display response
        if response.get('status') == 'success':
            console.print("✅ HL7 message processed successfully")
            console.print(f"📋 Response: {response.get('message_type', 'Unknown')} - {response.get('status', 'Unknown')}")
        else:
            console.print("❌ HL7 message processing failed")
            console.print(f"📋 Error: {response.get('error', 'Unknown error')}")
            
    except Exception as e:
        console.print(f"❌ HL7 testing failed: {str(e)}")


def test_astm_processing():
    """Test ASTM message processing"""
    try:
        console.print("\n[bold blue]Testing ASTM Message Processing...[/bold blue]")
        
        # Sample ASTM message with header, patient, order, and result records
        sample_astm_message = """H|\\^&|||AnalyzerName|||||||||20231201120000
P|1||P001||Smith^John||19800115|M|||123 Main St^^City^ST^12345||555-0123|Dr. Johnson
O|1|S001||GLU^Glucose|R||20231201120000|||||||||Dr. Johnson
R|1|GLU^Glucose|120|mg/dL|70-100|H|||F|||20231201121500|AnalyzerName
L|1|N"""
        
        console.print("📨 Processing sample ASTM message...")
        console.print(f"Message preview: {sample_astm_message[:80]}...")
        
        # Import and test ASTM handler
        from src.communication.astm_handler import astm_handler
        
        # Process the message
        response = astm_handler.process_message(sample_astm_message)
        
        # Display response
        if response.get('status') == 'success':
            console.print("✅ ASTM message processed successfully")
            records_processed = response.get('records_processed', 0)
            console.print(f"📋 Records processed: {records_processed}")
            
            # Show details of processed records
            for record in response.get('records', []):
                record_type = record.get('type')
                if record_type == 'P':
                    patient_name = record.get('data', {}).get('patient_name', 'Unknown')
                    console.print(f"   👤 Patient: {patient_name}")
                elif record_type == 'R':
                    test_info = record.get('data', {}).get('test_information', {})
                    test_name = test_info.get('test_name', test_info.get('test_id', 'Unknown'))
                    value = record.get('data', {}).get('measurement_value', 'Unknown')
                    units = record.get('data', {}).get('units', '')
                    console.print(f"   🧪 Result: {test_name} = {value} {units}")
        else:
            console.print("❌ ASTM message processing failed")
            console.print(f"📋 Error: {response.get('error', 'Unknown error')}")
            
    except Exception as e:
        console.print(f"❌ ASTM testing failed: {str(e)}")


def display_patients():
    """Display all patients in the system"""
    try:
        console.print("\n[bold blue]Patient List:[/bold blue]")
        
        with get_session() as session:
            patients = session.query(Patient).all()
            
            if not patients:
                console.print("No patients found in the system.")
                return
            
            # Create patients table
            table = Table(title="Registered Patients")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="white")
            table.add_column("DOB", style="green")
            table.add_column("Gender", style="magenta")
            table.add_column("Age", style="yellow")
            
            for patient in patients:
                table.add_row(
                    patient.patient_id,
                    patient.full_name,
                    patient.date_of_birth.strftime("%Y-%m-%d") if patient.date_of_birth else "N/A",
                    patient.gender or "N/A",
                    str(patient.age) if patient.age else "N/A"
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"❌ Failed to display patients: {str(e)}")


def display_equipment():
    """Display all equipment in the system"""
    try:
        console.print("\n[bold blue]Equipment List:[/bold blue]")
        
        with get_session() as session:
            equipment = session.query(Equipment).all()
            
            if not equipment:
                console.print("No equipment found in the system.")
                return
            
            # Create equipment table
            table = Table(title="Laboratory Equipment")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="white")
            table.add_column("Type", style="green")
            table.add_column("Status", style="magenta")
            table.add_column("Location", style="yellow")
            
            for eq in equipment:
                status_icon = "🟢" if eq.is_online else "🔴"
                table.add_row(
                    eq.equipment_id,
                    eq.name,
                    eq.equipment_type.value.replace("_", " ").title(),
                    f"{status_icon} {eq.status.value.title()}",
                    eq.location or "N/A"
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"❌ Failed to display equipment: {str(e)}")


def interactive_menu():
    """Display interactive menu for LIS operations"""
    while True:
        console.print("\n[bold green]LIS System Menu:[/bold green]")
        console.print("  1. Display System Status")
        console.print("  2. View Patients")
        console.print("  3. View Equipment")
        console.print("  4. Test HL7 Processing")
        console.print("  5. Test ASTM Processing")
        console.print("  6. Create Sample Data")
        console.print("  0. Exit")
        
        try:
            choice = input("\nSelect an option (0-6): ").strip()
            
            if choice == "1":
                display_system_status()
            elif choice == "2":
                display_patients()
            elif choice == "3":
                display_equipment()
            elif choice == "4":
                test_hl7_processing()
            elif choice == "5":
                test_astm_processing()
            elif choice == "6":
                create_sample_data()
            elif choice == "0":
                console.print("\n[bold blue]Thank you for using the LIS System![/bold blue]")
                break
            else:
                console.print("❌ Invalid option. Please select 0-6.")
                
        except KeyboardInterrupt:
            console.print("\n\n[bold blue]Thank you for using the LIS System![/bold blue]")
            break
        except Exception as e:
            console.print(f"❌ Error: {str(e)}")


def main():
    """Main entry point for the LIS system"""
    try:
        # Display welcome message
        display_welcome()
        
        # Initialize database
        if not initialize_database():
            console.print("❌ Failed to initialize database. Exiting...")
            sys.exit(1)
        
        # Show initial system status
        display_system_status()
        
        # Start interactive menu
        interactive_menu()
        
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]System shutdown requested...[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        console.print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 