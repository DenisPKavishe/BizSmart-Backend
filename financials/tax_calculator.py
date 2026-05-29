# financials/tax_calculator.py

from decimal import Decimal

class TaxCalculator:
    VAT_RATE = Decimal('0.18')
    SDL_RATE = Decimal('0.035')
    
    INCOME_TAX_BRACKETS = [
        (Decimal('270000'), Decimal('0')),
        (Decimal('520000'), Decimal('0.08')),
        (Decimal('760000'), Decimal('0.20')),
        (Decimal('1000000'), Decimal('0.25')),
        (Decimal('inf'), Decimal('0.30')),
    ]
    
    @classmethod
    def calculate_vat(cls, amount, inclusive=True):
        if inclusive:
            vat = amount - (amount / (1 + cls.VAT_RATE))
        else:
            vat = amount * cls.VAT_RATE
        return round(vat, 2)
    
    @classmethod
    def calculate_income_tax(cls, annual_profit):
        remaining = annual_profit
        tax = Decimal('0')
        prev_limit = Decimal('0')
        
        for limit, rate in cls.INCOME_TAX_BRACKETS:
            if remaining <= 0:
                break
            taxable = min(remaining, limit - prev_limit)
            tax += taxable * rate
            remaining -= taxable
            prev_limit = limit
        
        return round(tax, 2)
    
    @classmethod
    def calculate_paye(cls, monthly_salary):
        annual_tax = cls.calculate_income_tax(monthly_salary * 12)
        return round(annual_tax / 12, 2)
    
    @classmethod
    def calculate_sdl(cls, monthly_salary):
        return round(monthly_salary * cls.SDL_RATE, 2)