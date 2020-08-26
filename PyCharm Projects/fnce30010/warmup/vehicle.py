from abc import ABC, abstractmethod

'''

VARIABLES - INSTANCE and CLASS
==============================

to access class variables we can do either self.class_variable or ClassName.class_variable
to access the namespace of an instance, we can do instanceName.__dict__ - class variables wont show up here
if we do className.__dict__ we see the class variables here

if we attempt to change the class variable from an instance, it will simply create a local copy of that variable
in that instance instead of changing the class var
*** if we want to have a class variable, but some instances have it different, then we should make a class variable,
    but access it using self.instanceVariable, as by modifying this, we effectively create a new instance variable,
    but simply accessing it means we are accessing the class variable 
    
    BUT, if there's no use case for modifying the class variable, then access it using className.instanceVariable
    **************************

METHODS - REGULAR AND CLASS

regular methods - def func(self), self is the instance calling the method, automatically gets sent
CLASS method - just add a decorator to the top eg:

@classmethod
def set_raise_amount(cls, amount):
    cls.raise_amount = amount
    
now if we call className.set_raise_amount(1.04)
this will change the actual class variable to 1.04, where className is passed in as the initial cls argument

https://www.youtube.com/watch?v=rq8cL2XMM5M

    say if we wanted to create an alternative constructor we can do
    
    @classmethod
    def from_string(cls, otherarg):
        return cls(first, last, otherarg)
        #cls() here is equivalent to className()

*****
STATIC methods dont pass anything! they don't pass any self or cls
@staticmethod
def is_workday(day):
if day.weekday == 5:
    return true
    
if we don't access the instance or class variable anywhere, it should be a static method!
if no "self" or "cls" should be static



'''


class Vehicle(ABC):
    """
    Abstract Vehicle class.
    """
    __subclass = None

    def __init__(self, brand, model, capacity):
        """Constructor for the Vehicle class.
        :param brand: Brand of the car.
        :param model: Model of the car.
        :param capacity: Total fuel capacity of the car.
        """

        self._brand = brand
        self._model = model
        self._fuel = 0
        self._capacity = capacity

    @property
    def brand(self):
        return self._brand

    @brand.setter
    def brand(self, value):
        self._brand = value

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    @property
    def fuel(self):
        return self._fuel

    @fuel.setter
    def fuel(self, value):
        self._fuel = value

    @property
    def capacity(self):
        return self._capacity

    @capacity.setter
    def capacity(self, value):
        self._capacity = value

    @abstractmethod
    def go(self, distance):
        """
        Let the car go for the given distance.If the car does not have enough fuel,
        then it travels as far as it can!
        :param distance: Travel Distance in kms.
        :return: The actual travelled distance.
        """
        pass

    @abstractmethod
    def refuel(self, fuel):
        """
        Refuel the car with the given fuel amount.
        :param fuel: amount of fuel to refill.
        :return:"""
        pass

    @abstractmethod
    def can_go(self, distance):
        """
        Check if the car can travel the given distance based on the current fuel level.
        :param distance: Distance in kms.
        :return:True if the car can travel the distance, False otherwise
        """
        pass

    def print_info(self):
        print(f"{self._model}: {self._brand}")
