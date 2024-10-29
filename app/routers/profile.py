from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.database.queues.get_user_by_id import get_user_by_id
from app.database.queues.put_user import put_user

from app.bot.create_check import create_check
from app.bot.convert_btc_to_usdt import convert_btc_to_usdt
from app.bot.get_balance import get_balance

from app.keyboards.profile import profile_keyboard
from app.keyboards.main import main_keyboard


class Profile(StatesGroup):
    update_referral = State()
    withdraw = State()


profile_router = Router()


@profile_router.message(F.text == 'Профиль 👤')
async def profile(message: Message, state: FSMContext) -> None:
    """
    Handles "Профиль" button in main menu. Checks if user is in the database, 
    clears state, deletes message, fetches user data and sends message with 
    user's profile information.
    """
    try:
        await state.clear()

        await message.delete()
        
        user = await get_user_by_id(message.from_user.id)
        
        btc_balance = '{:.8f}'.format(user[0])
        
        converted_balance = await convert_btc_to_usdt(float(btc_balance))
        usdt_equivalent = '{:.2f}'.format(converted_balance)
        
        referrals_amount = user[1]
        play_referral_code = user[7]
        if play_referral_code is None:
            play_referral_code = 'не установлен'

        if user:
            content = f'Пользователь: {message.from_user.first_name}\n\n' \
                    f'BTC Баланс: <code>{btc_balance}</code> ₿\nUSDT эквивалент: {usdt_equivalent} ₮\n\n' \
                    f'Количество зарегистрированных рефералов: {referrals_amount}\n\n' \
                    f'Код реферала (для регистрации): <code>{user[2]}</code>\n\n' \
                    f'Код реферала (для игры): <code>{user[7]}</code>'

            await message.answer(content, reply_markup=profile_keyboard(), parse_mode='HTML')
    except Exception as e:
        print(f'Profile error: {e}')


@profile_router.callback_query(F.data == 'update_referral')
async def update_referral(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handles "Обновить реферальный код" button in profile menu. Checks if user is in the database, 
    clears state, deletes message, fetches user data and sends message with 
    prompt to enter new referral code.
    """
    try:
        await state.set_state(Profile.update_referral)

        content = 'Введите новый реферальный код 🔑'

        await callback.message.answer(content)
    except Exception as e:
        print(f'Update referral error: {e}')


@profile_router.message(Profile.update_referral)
async def update_referral_new(message: Message, state: FSMContext) -> None:
    """
    Handles message with new referral code in "update_referral" state. Checks if user is in the database, 
    updates user's referral code, clears state, deletes message, and sends message with 
    confirmation of successful update.
    """
    try:
        await put_user(message.from_user.id, play_referral_code=message.text)

        await state.clear()

        content = 'Реферальный код обновлен ✅'

        await message.answer(content, reply_markup=main_keyboard())
    except Exception as e:
        print(f'Update referral error: {e}')


@profile_router.callback_query(F.data == 'withdraw')
async def withdraw(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handles "Вывести" button in profile menu. Checks if user is in the database, 
    clears state, deletes message, fetches user data and sends message with 
    prompt to enter amount of BTC to withdraw.
    """
    try:
        await state.set_state(Profile.withdraw)

        content = 'Введите количество BTC для вывода.'

        await callback.message.answer(content)
    except Exception as e:
        print(f'Withdraw error: {e}')

    
@profile_router.message(Profile.withdraw)
async def withdraw_btc(message: Message, state: FSMContext) -> None:
    """
    Handles message with amount of BTC to withdraw in "withdraw" state. Checks if user is in the database, 
    checks if user has enough balance to withdraw, checks if app has enough balance to withdraw, 
    creates a check, updates user's balance, sends message with check information, and clears state.
    """
    try:
        user = await get_user_by_id(message.from_user.id)
        btc_balance = user[0]
        app_balance = await get_balance()

        converted_withdraw = await convert_btc_to_usdt(float(message.text))

        if btc_balance < float(message.text):
            content = 'Ваш баланс меньше введенной суммы. Попробуйте ещё раз 🙂'

            await message.answer(content)
        elif app_balance < converted_withdraw:
            content = 'Ошибка при выводе. Попробуйте ещё раз 🙂'

            await message.answer(content)
        else:
            check = await create_check(converted_withdraw)
            if check == 400:
                await message.answer('Введите сумму эквивалентную или больше 0.02 $ USD 😉')

                return

            content = f'Чек {check.check_id} на сумму {'{:.8f}'.format(check.amount)} {check.asset} создан в {check.created_at} ✅\n' \
                      f'Активация по ссылке: {check.bot_check_url}'
            
            await put_user(message.from_user.id, btc_balance=btc_balance - float(message.text))
            
            await message.answer(content, reply_markup=main_keyboard())

            await state.clear()
    except Exception as e:
        print(f'Withdraw BTC error: {e}')