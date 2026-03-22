"""
Admin Tool — SahamBot MY
Manage users + tengok pilot stats
"""
import sys
from database import init_db, set_tier, get_user, get_pilot_stats, ensure_daily_usage_current


def main():
    init_db()

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python admin.py activate <user_id>          — Set Premium")
        print("  python admin.py pro <user_id>               — Set Pro")
        print("  python admin.py deactivate <user_id>        — Set Free")
        print("  python admin.py check <user_id>             — Semak user")
        print("  python admin.py stats                       — Pilot stats")
        return

    action = sys.argv[1]

    if action == "stats":
        stats = get_pilot_stats()
        print("\n📊 PILOT STATS — SahamBot MY")
        print("=" * 40)
        print(f"Total Users     : {stats['total_users']}")
        print(f"Premium/Pro     : {stats['premium_users']}")
        conversion = (stats['premium_users'] / stats['total_users'] * 100) if stats['total_users'] > 0 else 0
        print(f"Conversion Rate : {conversion:.1f}%")
        print(f"Total Analyses  : {stats['total_analyses']}")
        print("\n📅 Timeframe Usage:")
        for tf, count in stats['timeframe_usage']:
            print(f"  {tf}: {count}x")
        print("\n🕯️ Candle Count Usage:")
        for cc, count in stats['candle_usage']:
            print(f"  {cc} candle: {count}x")
        print("\n📥 Input Method:")
        for method, count in stats['input_method']:
            print(f"  {method}: {count}x")
        return

    if len(sys.argv) < 3:
        print("❗ Masukkan user_id.")
        return

    user_id = int(sys.argv[2])

    if action == "activate":
        set_tier(user_id, 1)
        print(f"✅ User {user_id} → PREMIUM")
    elif action == "pro":
        set_tier(user_id, 2)
        print(f"✅ User {user_id} → PRO")
    elif action == "deactivate":
        set_tier(user_id, 0)
        print(f"⛔ User {user_id} → FREE")
    elif action == "check":
        ensure_daily_usage_current(user_id)
        user = get_user(user_id)
        if user:
            tier_label = ["FREE", "PREMIUM", "PRO"][user[2]]
            print(f"\n👤 User: {user[1]} (ID: {user[0]})")
            print(f"   Tier    : {tier_label}")
            print(f"   Usage   : {user[3]} analisa hari ini")
            print(f"   Joined  : {user[5]}")
        else:
            print(f"❌ User {user_id} tidak dijumpai.")
    else:
        print("❗ Action tidak dikenali.")


if __name__ == "__main__":
    main()