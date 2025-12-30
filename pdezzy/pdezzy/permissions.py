"""
Custom permission classes for Agent, Seller, and Buyer apps
"""
from rest_framework.permissions import BasePermission
from agent.models import Agent
from seller.models import Seller
from buyer.models import Buyer


class IsAgent(BasePermission):
    """
    Permission to check if the user is an Agent instance
    Allows authenticated agents to access agent-specific endpoints
    """
    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is an Agent instance
        try:
            return isinstance(request.user, Agent)
        except:
            return False


class IsSeller(BasePermission):
    """
    Permission to check if the user is a Seller instance
    Allows authenticated sellers to access seller-specific endpoints
    """
    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a Seller instance
        try:
            return isinstance(request.user, Seller)
        except:
            return False


class IsBuyer(BasePermission):
    """
    Permission to check if the user is a Buyer instance
    Allows authenticated buyers to access buyer-specific endpoints
    """
    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a Buyer instance
        try:
            return isinstance(request.user, Buyer)
        except:
            return False
