from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, time, datetime
import json
from .models import Room, TimeSlot


class RoomsAPITestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test rooms
        self.active_room = Room.objects.create(
            name="Test Escape Room",
            slug="test-escape-room",
            short_description="A thrilling escape room experience",
            full_description="This is a detailed description of our amazing escape room with puzzles and challenges.",
            base_price=30.00,
            is_active=True
        )
        
        self.inactive_room = Room.objects.create(
            name="Inactive Room",
            slug="inactive-room",
            short_description="This room is not active",
            full_description="This room should not appear in API responses.",
            base_price=25.00,
            is_active=False
        )
        
        # Create test time slots
        today = date.today()
        self.active_slot = TimeSlot.objects.create(
            room=self.active_room,
            date=today,
            time=time(14, 0),  # 2:00 PM
            status='active'
        )
        
        self.reserved_slot = TimeSlot.objects.create(
            room=self.active_room,
            date=today,
            time=time(16, 0),  # 4:00 PM
            status='reserved'
        )

    def test_list_rooms_success(self):
        """Test GET /api/rooms/ returns only active rooms"""
        response = self.client.get('/api/rooms/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return only active rooms
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.active_room.id)
        self.assertEqual(data[0]['name'], self.active_room.name)
        self.assertEqual(data[0]['slug'], self.active_room.slug)
        self.assertEqual(data[0]['is_active'], True)
        self.assertEqual(float(data[0]['base_price']), float(self.active_room.base_price))

    def test_list_rooms_empty(self):
        """Test GET /api/rooms/ when no active rooms exist"""
        # Deactivate all rooms
        Room.objects.update(is_active=False)
        
        response = self.client.get('/api/rooms/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)

    def test_get_room_success(self):
        """Test GET /api/rooms/{id}/ returns room details"""
        response = self.client.get(f'/api/rooms/{self.active_room.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['id'], self.active_room.id)
        self.assertEqual(data['name'], self.active_room.name)
        self.assertEqual(data['slug'], self.active_room.slug)
        self.assertEqual(data['short_description'], self.active_room.short_description)
        self.assertEqual(data['full_description'], self.active_room.full_description)
        self.assertEqual(float(data['base_price']), float(self.active_room.base_price))
        self.assertEqual(data['is_active'], True)

    def test_get_room_not_found(self):
        """Test GET /api/rooms/{id}/ with non-existent room ID"""
        response = self.client.get('/api/rooms/99999/')
        
        self.assertEqual(response.status_code, 404)

    def test_get_inactive_room_not_found(self):
        """Test GET /api/rooms/{id}/ with inactive room returns 404"""
        response = self.client.get(f'/api/rooms/{self.inactive_room.id}/')
        
        self.assertEqual(response.status_code, 404)

    def test_get_room_availability_success(self):
        """Test GET /api/rooms/{id}/availability/ returns available slots"""
        today = date.today()
        response = self.client.get(f'/api/rooms/{self.active_room.id}/availability/?date={today}')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['room_id'], self.active_room.id)
        self.assertEqual(data['room_name'], self.active_room.name)
        self.assertEqual(data['date'], str(today))
        
        # Should only return active slots, not reserved ones
        self.assertEqual(len(data['available_times']), 1)
        self.assertEqual(data['available_times'][0]['id'], self.active_slot.id)
        self.assertEqual(data['available_times'][0]['status'], 'active')
        self.assertEqual(data['available_times'][0]['time'], '14:00:00')

    def test_get_room_availability_no_date(self):
        """Test GET /api/rooms/{id}/availability/ without date parameter uses today"""
        response = self.client.get(f'/api/rooms/{self.active_room.id}/availability/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['date'], str(date.today()))

    def test_get_room_availability_no_slots(self):
        """Test GET /api/rooms/{id}/availability/ when no slots available"""
        # Use a future date with no slots
        future_date = date(2025, 12, 31)
        response = self.client.get(f'/api/rooms/{self.active_room.id}/availability/?date={future_date}')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['room_id'], self.active_room.id)
        self.assertEqual(data['date'], str(future_date))
        self.assertEqual(len(data['available_times']), 0)

    def test_get_room_availability_room_not_found(self):
        """Test GET /api/rooms/{id}/availability/ with non-existent room"""
        response = self.client.get('/api/rooms/99999/availability/')
        
        self.assertEqual(response.status_code, 404)

    def test_get_room_availability_inactive_room(self):
        """Test GET /api/rooms/{id}/availability/ with inactive room"""
        response = self.client.get(f'/api/rooms/{self.inactive_room.id}/availability/')
        
        self.assertEqual(response.status_code, 404)

    def test_room_schema_validation(self):
        """Test that room schema includes all required fields"""
        response = self.client.get(f'/api/rooms/{self.active_room.id}/')
        data = response.json()
        
        required_fields = [
            'id', 'name', 'slug', 'short_description', 
            'full_description', 'hero_image', 'thumbnail_image', 
            'base_price', 'is_active'
        ]
        
        for field in required_fields:
            self.assertIn(field, data)

    def test_availability_schema_validation(self):
        """Test that availability response schema includes all required fields"""
        response = self.client.get(f'/api/rooms/{self.active_room.id}/availability/')
        data = response.json()
        
        # Check main response fields
        required_fields = ['room_id', 'room_name', 'date', 'available_times']
        for field in required_fields:
            self.assertIn(field, data)
        
        # Check time slot fields if any slots exist
        if data['available_times']:
            slot_fields = ['id', 'date', 'time', 'status']
            for field in slot_fields:
                self.assertIn(field, data['available_times'][0])

    def test_multiple_rooms_availability(self):
        """Test availability endpoint works correctly with multiple rooms"""
        # Create another room with time slots
        room2 = Room.objects.create(
            name="Second Room",
            slug="second-room",
            short_description="Another room",
            full_description="Second room description",
            base_price=35.00,
            is_active=True
        )
        
        today = date.today()
        TimeSlot.objects.create(
            room=room2,
            date=today,
            time=time(15, 0),  # 3:00 PM
            status='active'
        )
        
        # Test first room
        response1 = self.client.get(f'/api/rooms/{self.active_room.id}/availability/?date={today}')
        data1 = response1.json()
        
        # Test second room
        response2 = self.client.get(f'/api/rooms/{room2.id}/availability/?date={today}')
        data2 = response2.json()
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        # Each room should have its own availability
        self.assertEqual(data1['room_id'], self.active_room.id)
        self.assertEqual(data2['room_id'], room2.id)
        self.assertNotEqual(data1['available_times'][0]['time'], data2['available_times'][0]['time'])
