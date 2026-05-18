"""Arena event catalog — 10 economic scenarios with forced choices."""

from dataclasses import dataclass, field


@dataclass
class Choice:
    index: int
    label: str
    description: str


@dataclass
class Outcome:
    choice_index: int
    money_delta: float
    happiness_delta: float
    description: str


@dataclass
class Event:
    name: str
    description: str
    choices: list[Choice]
    resolve: "callable"  # (choice_index, luck) -> Outcome


def _investment(choice: int, luck: float) -> Outcome:
    if choice == 1:
        return Outcome(1, 0, 0, "Kept cash safe. Nothing gained, nothing lost.")
    if choice == 2:
        amount = 100
        if luck > 0.5:
            gain = int(amount * 1.5 * luck)
            return Outcome(2, gain, 0.1, f"Moderate investment paid off! +${gain}")
        loss = int(amount * 0.5)
        return Outcome(2, -loss, -0.05, f"Investment dipped. -${loss}")
    amount = 300
    if luck > 0.6:
        gain = int(amount * 3 * luck)
        return Outcome(3, gain, 0.2, f"Big bet paid off huge! +${gain}")
    loss = int(amount * 0.8)
    return Outcome(3, -loss, -0.15, f"Big bet crashed. -${loss}")


def _job_offer(choice: int, luck: float) -> Outcome:
    if choice == 1:
        return Outcome(1, 50, 0.0, "Stayed put. Steady paycheck, no growth.")
    if choice == 2:
        if luck > 0.4:
            return Outcome(2, 150, 0.1, "New job is great! Better pay and exciting work.")
        return Outcome(2, -30, -0.1, "New job was a mistake. Toxic environment.")
    if luck > 0.3:
        return Outcome(3, 0, 0.15, "Freelancing is liberating! Slow start but freedom.")
    return Outcome(3, -100, -0.1, "No clients. Freelancing is lonely and broke.")


def _gambling(choice: int, luck: float) -> Outcome:
    if choice == 1:
        return Outcome(1, 0, 0, "Walked away. Smart move... or missed opportunity?")
    if choice == 2:
        if luck > 0.45:
            return Outcome(2, 80, 0.1, "Small bet, small win. +$80")
        return Outcome(2, -50, -0.05, "Small bet, small loss. -$50")
    if luck > 0.7:
        return Outcome(3, 500, 0.25, "ALL IN WINS! The rush is incredible! +$500")
    return Outcome(3, -300, -0.2, "All in... all gone. Devastating loss. -$300")


def _skill_workshop(choice: int, luck: float) -> Outcome:
    if choice == 1:
        return Outcome(1, 0, 0, "Skipped it. Time is money... or is money time?")
    if choice == 2:
        return Outcome(2, -50, 0.1, "Learned something useful. Worth the cost.")
    return Outcome(3, -200, 0.05 if luck > 0.5 else -0.05,
                   "Expensive bootcamp. " + ("Great connections!" if luck > 0.5 else "Disappointing content."))


def _friend_needs_money(choice: int, luck: float) -> Outcome:
    if choice == 1:
        return Outcome(1, 0, -0.05, "Said no. Feel guilty but wallet is safe.")
    if choice == 2:
        if luck > 0.6:
            return Outcome(2, 50, 0.15, "Friend paid back with interest! +$50 and a grateful ally.")
        return Outcome(2, -100, -0.05, "Lent $100. Never saw it again.")
    return Outcome(3, -50, 0.1, "Gave $50, no strings. Friend is grateful.")


def _health_scare(choice: int, luck: float) -> Outcome:
    if choice == 1:
        if luck < 0.3:
            return Outcome(1, 0, -0.2, "Ignored it. Condition worsened. Now in real trouble.")
        return Outcome(1, 0, 0, "Ignored it. Turned out to be nothing.")
    if choice == 2:
        return Outcome(2, -200, 0.1, "Saw the doctor. Caught it early. Expensive but worth it.")
    return Outcome(3, -50, 0.05, "Home remedies. Feeling a bit better, saved some cash.")


def _rent_crisis(choice: int, luck: float) -> Outcome:
    if choice == 1:
        if luck > 0.5:
            return Outcome(1, -50, 0.05, "Negotiated a smaller increase. -$50/month.")
        return Outcome(1, -150, -0.05, "Negotiation failed. Paying full increase.")
    if choice == 2:
        return Outcome(2, -300, -0.1, "Moving costs hurt but found a cheaper place.")
    return Outcome(3, -100, -0.15, "Got a roommate. Saved money but lost privacy.")


def _windfall(choice: int, luck: float) -> Outcome:
    if choice == 1:
        return Outcome(1, 200, 0.05, "Saved the windfall. Responsible and boring.")
    if choice == 2:
        return Outcome(2, 0, 0.15, "Spent it all on experiences. No regrets! ...right?")
    gain = int(200 * luck * 2)
    if luck > 0.5:
        return Outcome(3, gain, 0.1, f"Reinvested and it grew! +${gain}")
    loss = int(200 * 0.6)
    return Outcome(3, -loss, -0.1, f"Reinvested and lost. -${loss}")


def _reputation_test(choice: int, luck: float) -> Outcome:
    if choice == 1:
        return Outcome(1, 0, -0.05, "Stayed quiet. Safe but feels cowardly.")
    if choice == 2:
        if luck > 0.4:
            return Outcome(2, 100, 0.15, "Spoke up. People respect the honesty. +$100 bonus.")
        return Outcome(2, -50, -0.1, "Spoke up. Made enemies. Lost a client.")
    return Outcome(3, 0, 0.0, "Deflected diplomatically. Status quo maintained.")


def _final_gambit(choice: int, luck: float) -> Outcome:
    if choice == 1:
        return Outcome(1, 0, 0.05, "Played it safe. Locked in what you have.")
    if choice == 2:
        if luck > 0.5:
            return Outcome(2, 300, 0.2, "Calculated risk paid off! Strong finish. +$300")
        return Outcome(2, -150, -0.1, "Risk didn't pay. Lost $150 at the end.")
    if luck > 0.65:
        return Outcome(3, 1000, 0.3, "MOONSHOT! Everything came together! +$1000!")
    return Outcome(3, -500, -0.25, "Moonshot crashed. Lost $500. Painful ending.")


EVENTS: list[Event] = [
    Event(
        name="Investment Opportunity",
        description="A startup founder pitches you. Early stage, high risk, could be huge.",
        choices=[
            Choice(1, "Pass", "Keep your cash safe"),
            Choice(2, "Invest $100", "Moderate bet on potential"),
            Choice(3, "Invest $300", "Go big or go home"),
        ],
        resolve=_investment,
    ),
    Event(
        name="Job Offer",
        description="A recruiter calls. New company, better title, but unknown culture.",
        choices=[
            Choice(1, "Stay", "Keep your current stable job"),
            Choice(2, "Switch", "Take the new offer"),
            Choice(3, "Freelance", "Quit both and go independent"),
        ],
        resolve=_job_offer,
    ),
    Event(
        name="Casino Night",
        description="Friends invite you to the casino. You can feel the luck tonight.",
        choices=[
            Choice(1, "Walk away", "Not worth the risk"),
            Choice(2, "Small bet", "Play it safe with $50"),
            Choice(3, "All in", "Put $300 on the table"),
        ],
        resolve=_gambling,
    ),
    Event(
        name="Skill Workshop",
        description="A weekend workshop in a skill you've been curious about.",
        choices=[
            Choice(1, "Skip", "Save time and money"),
            Choice(2, "Basic course ($50)", "Learn the fundamentals"),
            Choice(3, "Premium bootcamp ($200)", "Go all in on learning"),
        ],
        resolve=_skill_workshop,
    ),
    Event(
        name="Friend Needs Money",
        description="A close friend is in trouble and asks to borrow $100.",
        choices=[
            Choice(1, "Decline", "You can't afford the risk"),
            Choice(2, "Lend $100", "Help them out, hope they pay back"),
            Choice(3, "Give $50", "Help a little, no strings attached"),
        ],
        resolve=_friend_needs_money,
    ),
    Event(
        name="Health Scare",
        description="Something doesn't feel right. Could be nothing, could be serious.",
        choices=[
            Choice(1, "Ignore it", "Probably nothing. Push through."),
            Choice(2, "See a doctor ($200)", "Better safe than sorry"),
            Choice(3, "Home remedies ($50)", "Try to handle it yourself"),
        ],
        resolve=_health_scare,
    ),
    Event(
        name="Rent Crisis",
        description="Your landlord announces a 30% rent increase next month.",
        choices=[
            Choice(1, "Negotiate", "Try to talk them down"),
            Choice(2, "Move", "Find a cheaper place"),
            Choice(3, "Get a roommate", "Split costs, lose space"),
        ],
        resolve=_rent_crisis,
    ),
    Event(
        name="Unexpected Windfall",
        description="You find $200 you forgot about in an old jacket pocket.",
        choices=[
            Choice(1, "Save it", "Straight to savings"),
            Choice(2, "Spend it", "Treat yourself"),
            Choice(3, "Reinvest", "Try to grow it"),
        ],
        resolve=_windfall,
    ),
    Event(
        name="Reputation Test",
        description="Your boss takes credit for your work in a big meeting.",
        choices=[
            Choice(1, "Stay quiet", "Don't rock the boat"),
            Choice(2, "Speak up", "Claim your credit publicly"),
            Choice(3, "Deflect", "Handle it diplomatically later"),
        ],
        resolve=_reputation_test,
    ),
    Event(
        name="Final Gambit",
        description="Last chance. One big opportunity before the game ends.",
        choices=[
            Choice(1, "Lock it in", "Protect what you've earned"),
            Choice(2, "Calculated risk", "One more smart bet"),
            Choice(3, "Moonshot", "Everything on one play"),
        ],
        resolve=_final_gambit,
    ),
]
