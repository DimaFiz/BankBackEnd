"""Test for bank system"""

import pytest
from pytest import fixture
import sys
import os

sys.path.append(os.path.abspath("../bank.py"))

from bank import *


# =============================== FIXTURES ===============================
@pytest.fixture
def sample_bank():
    """Создание тестового банка"""
    return Bank(name="Тестовый Банк", bic="044525974")


@pytest.fixture
def sample_user_data():
    """Тестовые данные пользователя"""
    return {
        "last_name": "Иванов",
        "first_name": "Иван",
        "pin": "1234",
        "phone": "+79161234567",
        "payment_system": "MIR"
    }


@pytest.fixture
def sample_card(sample_bank, sample_user_data):
    """Создание тестовой карты"""
    card = sample_bank.apply_for_card(
        last_name=sample_user_data["last_name"],
        first_name=sample_user_data["first_name"],
        pin=sample_user_data["pin"],
        phone=sample_user_data["phone"],
        payment_system=sample_user_data["payment_system"]
    )
    return card


@pytest.fixture
def two_cards(sample_bank):
    """Создание двух карт для тестов переводов"""
    card1 = sample_bank.apply_for_card(
        last_name="Петров",
        first_name="Петр",
        pin="1111",
        phone="+79161111111",
        payment_system="VISA"
    )

    card2 = sample_bank.apply_for_card(
        last_name="Сидорова",
        first_name="Анна",
        pin="2222",
        phone="+79162222222",
        payment_system="MASTERCARD"
    )

    return card1, card2


# =============================== ТЕСТЫ КЛАССА BANK ===============================
class TestBank:
    """Тесты для класса Bank"""

    def test_bank_initialization(self, sample_bank):
        """Тест инициализации банка"""
        assert sample_bank.name == "Тестовый Банк"
        assert sample_bank.bic == "044525974"
        assert isinstance(sample_bank.customers, dict)
        assert isinstance(sample_bank.accounts, dict)
        assert isinstance(sample_bank.cards, dict)
        assert isinstance(sample_bank.transaction_log, list)

    def test_luhn_algorithm(self, sample_bank):
        """Тест алгоритма Луна для проверки номеров карт"""
        # Тестовые данные для алгоритма Луна
        test_cases = [
            ("220400000000000", "6"),  # MIR
            ("400000000000000", "6"),  # VISA
            ("510000000000000", "3"),  # MASTERCARD
        ]

        for number15, expected_check in test_cases:
            result = sample_bank._luhn(number15)
            assert str(result) == expected_check

    def test_generate_pan(self, sample_bank):
        """Тест генерации PAN номера"""
        pan = sample_bank._generate_pan("MIR")

        # Проверка формата
        assert len(pan) == 16  # 16 цифр
        assert pan.isdigit()

        # Проверка BIN кода
        assert pan.startswith(BIN_BY_SYSTEM["MIR"])

        # Проверка валидности через алгоритм Луна
        number15 = pan[:15]
        check_digit = int(pan[15])
        calculated_check = sample_bank._luhn(number15)
        assert check_digit == calculated_check

    def test_next_account_number(self, sample_bank):
        """Тест генерации номера счета"""
        account_number = sample_bank._next_account_number()

        # Проверка длины
        assert len(account_number) == 20

        # Проверка структуры
        assert account_number.startswith(ACCOUNT_TYPE_CODE + ACCOUNT_CURRENCY)

        # Проверка контрольной цифры
        bic_tail = sample_bank.bic[-3:]
        digits = [int(d) for d in bic_tail + account_number]
        weights = [7, 1, 3] * 8
        weighted = [a * b for a, b in zip(digits, weights)]
        control_sum = sum(x % 10 for x in weighted)
        assert control_sum % 10 == 0

    def test_apply_for_card_new_user(self, sample_bank, sample_user_data):
        """Тест выпуска карты для нового пользователя"""
        initial_user_count = len(sample_bank.customers)
        initial_card_count = sum(len(cards) for cards in sample_bank.cards.values())

        card = sample_bank.apply_for_card(**sample_user_data)

        # Проверка создания пользователя
        assert len(sample_bank.customers) == initial_user_count + 1
        assert any(user.phone == sample_user_data["phone"]
                   for user in sample_bank.customers.values())

        # Проверка создания карты
        total_cards = sum(len(cards) for cards in sample_bank.cards.values())
        assert total_cards == initial_card_count + 1

        # Проверка атрибутов карты
        assert isinstance(card, Card)
        assert card.payment_system == sample_user_data["payment_system"]
        assert card.currency == CARD_CURRENCY
        assert card.status == CardStatus.ACTIVE
        assert card.bank == sample_bank

        # Проверка PAN
        assert card.pan != EMPTY_PAN
        assert len(card.pan) == 16

        # Проверка дат
        assert card.issue_date is not None
        assert card.expiry_date is not None
        assert card.expiry_date.year == card.issue_date.year + 4

    def test_apply_for_card_existing_user(self, sample_bank, sample_user_data):
        """Тест выпуска второй карты для существующего пользователя"""
        # Выпускаем первую карту
        card1 = sample_bank.apply_for_card(**sample_user_data)
        user_id = card1.account.owner.user_id

        initial_user_count = len(sample_bank.customers)
        initial_user_cards = len(sample_bank.cards[user_id])

        # Выпускаем вторую карту
        card2 = sample_bank.apply_for_card(**sample_user_data)

        # Проверка, что пользователь не создается заново
        assert len(sample_bank.customers) == initial_user_count

        # Проверка, что карта добавлена пользователю
        assert len(sample_bank.cards[user_id]) == initial_user_cards + 1

        # Проверка, что карты разные
        assert card1.card_id != card2.card_id
        assert card1.pan != card2.pan


    def test_custom_card_class(self, sample_bank, sample_user_data):
        """Тест выпуска карты с пользовательским классом"""

        class CustomCard(Card):
            def __init__(self, *args, custom_field="default", **kwargs):
                super().__init__(*args, **kwargs)
                self.custom_field = custom_field

        card = sample_bank.apply_for_card(
            **sample_user_data,
            card_class=CustomCard,
            custom_field="test_value"
        )

        assert isinstance(card, CustomCard)
        assert card.custom_field == "test_value"
