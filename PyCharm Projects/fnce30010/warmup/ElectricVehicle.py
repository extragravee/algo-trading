from warmup.vehicle import Vehicle


class ElectricVehicle(Vehicle):

    def __init__(self, brand, model, capacity, efficiency):
        super().__init__(brand, model, capacity)
        self._efficiency = efficiency
        self._battery = 0.5 * capacity

    def can_go(self, distance):
        return distance <= self._battery * self._efficiency

    def go(self, distance):
        if self.can_go(distance):
            # travelled the required distance
            self._battery -= distance / self._efficiency
        else:
            print(f"Can only travel {self._efficiency * self._battery} kms")
            self._battery = 0

    def refuel(self, fuel):
        self._battery = max(self.capacity, self.capacity + fuel)

    def print_info(self):
        super().print_info()



