Chapter 1: The Dawn of Cryptography — From David Chaum to the Pioneers of Digital Gold

> *"Privacy is the power to selectively reveal oneself to the world."*
> *— David Chaum*

---

## Prologue: A Late Night in 1983

In 1983, President Reagan was signing the defense budget in the Oval Office; Apple launched the Lisa computer with a graphical interface; and the internet was still the exclusive domain of the military and academic institutions.

In an old building on the edge of the UC Berkeley campus, a thirty-two-year-old computer science doctoral student named David Chaum was staring at lines of code scrolling across his screen. His eyes were bloodshot, but the flames of idealism burned bright in his pupils.

Chaum's laboratory was in the basement, with no windows, the vents emitting a low, constant hum. The room smelled of old paper, electronic components, and cheap coffee mixed together. On shelves along the walls stood oscilloscopes, logic analyzers, modems, and an IBM personal computer — a luxury item at the time.

At this moment, Chaum sat in front of the IBM PC, the green glow of the fluorescent screen illuminating his pale face. On the screen was the code he had just completed — eCash, electronic cash.

"This is it," Chaum murmured to himself, his voice hoarse from hours of silence.

His fingers hovered over the keyboard, trembling slightly. He had been working continuously for forty-eight hours, sustained only by black coffee and energy bars. His body was exhausted, but his mind was extraordinarily alert.

Chaum took a deep breath and saved the code to a floppy disk. The disk drive emitted a harsh scratching sound as it read and wrote. The moment the indicator light went out, he knew that history had been rewritten.

"Anonymous digital payments," he said softly. "Real, untraceable, completely private electronic money. Not like credit cards — those leave transaction records that banks can monitor. Not like checks — those create payment trails that governments can follow. But like cash — once it changes hands, the transaction is complete, leaving no trace."

He stood up and paced around the cramped laboratory, his steps somewhat unsteady.

"In this digital age dawning upon us, without privacy protections, we will live in a panopticon. Every purchase will be recorded, every behavior monitored, every person as transparent as a glass mannequin."

He walked to the wall, where his fingers lightly touched a poster — the cover of George Orwell's 1984.

"But eCash will be a sword, severing the chains of surveillance."

Chaum walked to the teletype machine and began typing a message.

Recipient: cryptography mailing list (cryptography@list.enet.dec.com)
Subject: A New Electronic Payment Scheme — Electronic Cash (eCash)

"Fellow colleagues, I wish to share an idea with you. In this increasingly digital world, we face a fundamental question: How can we enjoy the convenience of electronic payments while protecting individual privacy and freedom?"

"Existing electronic payment systems — whether credit cards or electronic transfers — share a common flaw: they all rely on a Trusted Third Party (typically a bank or financial institution) to verify and record every transaction. This means this third party holds complete surveillance power over all transactions."

"I propose an entirely new scheme, which I call 'electronic cash.' At the core of this scheme is 'blind signature' technology — a technique that allows users to obtain a bank's valid signature on currency while the bank cannot know what it is signing and cannot trace where that currency ultimately flows."

He described the principles of blind signatures in detail: the user generates a random serial number, performs mathematical operations on it with the bank's public key ("blinding"), then sends the blinded data to the bank. The bank signs it with its private key and returns it to the user, who then performs the inverse operation ("unblinding"), ultimately obtaining a valid signature that the bank cannot trace.

"The result is this: the bank can verify that the money is genuine (because it carries the bank's valid signature), but it cannot know who the money was originally issued to, nor who ultimately spent it. Just like real cash — once withdrawn from the bank, its trail disappears into the vast sea of people."

Chaum pressed the send button. The teletype machine emitted a string of mechanical sounds, converting the message into electrical pulses that traveled through telephone lines to destinations thousands of miles away.

Then he stood up, walked to the sink, and splashed cold water on his haggard face. The mirror reflected a man with sunken eyes and stubble, but the light in those eyes still burned fiercely.

Outside the window, Berkeley's night sky was dotted with stars. In the summer of 1983, David Chaum had lit the first torch in the history of digital currency.

---

## Part One: The Flames of Idealism

### 1. Early Years: The Call of Cryptography

David Chaum was born in 1955 in a middle-class family in New York City. His father was an electrical engineer, and his mother was a middle school mathematics teacher. Though not wealthy, the family was filled with a deep respect for knowledge and education.

The young Chaum was not all that different from other children. He enjoyed taking apart radios, reading science fiction novels, and gazing at the stars. But he had an almost obsessive passion for mathematics.

"David has loved numbers since he was little," his mother recalled later. "He could sit in front of his building blocks for an entire day, not to build houses, but to study the relationships between geometric shapes."

This mathematical talent became increasingly evident as Chaum progressed through school. By high school, he had already self-studied university-level calculus and linear algebra. His math teacher said Chaum was one of the brightest students he had ever taught, "But he wasn't just smart — he had intuition. He could 'see' the things behind the mathematics, not just compute formulas."

In 1974, Chaum was admitted to the University of California, Berkeley with excellent grades, majoring in mathematics and computer science.

Berkeley at that time was one of the most radical and open academic centers in the United States. The aftermath of the anti-Vietnam War movement was still rippling through campus, the hippie culture was still flourishing, and the personal computer revolution was brewing in Silicon Valley. Young people questioned authority, pursued freedom, and believed that technology could change the world.

Chaum was quickly drawn to this atmosphere. But he was not a radical who took to the streets for protests; he chose a different path to pursue freedom — through mathematics and cryptography.

"I first encountered cryptography in 1976," Chaum recalled later. "That was when Whitfield Diffie and Martin Hellman published their famous paper, 'New Directions in Cryptography.' They proposed the concept of public-key cryptography, and it completely blew my mind."

That paper was indeed a milestone in the history of cryptography. Before that, cryptography was primarily the domain of the military, inaccessible to ordinary people. Key distribution was an almost unsolvable problem — if you wanted to communicate secretly with a friend, you had to first securely deliver the key to them, but if you could already exchange a key securely, why would you need encryption in the first place?

Diffie and Hellman's solution was revolutionary: use a pair of keys, a public key for encryption and a private key for decryption. The public key could be shared with anyone, while the private key had to be kept strictly secret. This way, anyone could send you an encrypted message using your public key, but only you — who held the private key — could decrypt it.

"It's like everyone having a publicly known mailbox address, but only you have the key to open it," Chaum said. "Such a simple and elegant idea, yet it completely transformed the possibilities for secure communication."

Chaum began studying cryptography obsessively. He read every paper he could find, attended every relevant lecture, and even wrote letters to Diffie and Hellman to ask questions. His doctoral research direction gradually crystallized — to make his own contributions to the field of cryptography.

In 1979, while a graduate student at Berkeley, Chaum met Professor Glenn Simmons, who would change the course of his life. Simmons was an authority in the field of cryptography, having worked at the International Business Machines Corporation (IBM) and Sandia National Laboratories, and had participated in U.S. government cryptography projects.

"When Professor Simmons first met me, he asked why I wanted to study cryptography," Chaum recalled. "I said, because I want to use mathematics to protect people's privacy. He laughed and said: 'Boy, cryptography is never just mathematics — it's about power. Whoever controls the cipher controls the information; whoever controls the information controls power.'"

Those words were deeply etched in Chaum's heart.

Under Simmons's guidance, Chaum began diving deep into various cryptographic protocols and applications. His first significant paper was published in 1981, titled "Untraceable Electronic Mail, Return Addresses, and Digital Pseudonyms." In this paper, he proposed a system that allowed users to send emails anonymously — even if an email was intercepted, the sender's true identity could not be traced.

"The core of that paper was a simple observation," Chaum explained. "If you route mail through a 'mix network' — a series of servers, each of which shuffles the order and alters the appearance of messages before forwarding them — then even if someone monitored the entire network, they could not determine which sender corresponded to which final message."

This idea later became the foundation of anonymous communication technologies (such as the Tor network), but at the time it was viewed more as a theoretical curiosity than a practical tool.

"The academic community's response was quite cold," Chaum said. "They said the idea was too complex, performance was too poor, and that nobody would ever really need anonymous email. But they overlooked a fundamental question: Why would people need anonymity? Because privacy is a basic human need, and in the digital age, that need will only grow stronger."

Undeterred by the lukewarm response, Chaum became even more resolute in his beliefs. He began contemplating an even bolder question: if anonymous communication was possible, what about anonymous payments?

### 2. Blind Signatures: A Flash of Insight

One late night in 1982, Chaum sat alone in the mathematics department library at Berkeley.

It was a typical California winter night, the mist outside making the glow of streetlamps hazy. The library was nearly empty, the heating system emitting a low hum. Dozens of papers lay scattered across the desk — some already yellowed, others still smelling of fresh printer ink. His coffee cup was empty, a brown ring staining the bottom.

He was studying the RSA public-key cryptosystem — the most famous and widely used public-key encryption algorithm at the time, invented in 1977 by three scientists at the Massachusetts Institute of Technology (MIT): Ronald Rivest, Adi Shamir, and Leonard Adleman. RSA's security was based on the difficulty of factoring large numbers — multiplying two large prime numbers is easy, but factoring their product back into the original primes is extremely difficult.

Chaum had been staring at the RSA formulas for hours.

The RSA signing process works like this: the signer uses their private key to "sign" a hash of a message, and anyone can use the signer's public key to verify that signature. If verification passes, it confirms that the message truly originated from the signer and has not been tampered with.

This was a perfect identity authentication mechanism. But it had a problem: the signer always knew what they were signing. If you wanted to obtain a bank's signature to prove you owned a sum of money, the bank would know the serial number of that money, enabling it to trace its flow.

"But what if..." Chaum murmured to himself, his pencil flying across the scratch paper as he calculated rapidly.

A wild idea took shape in his mind.

What if there was a method that allowed a bank to sign a piece of data without the bank knowing what it was signing? Like a person signing a document blindfolded — they know they are signing, but they do not know the document's contents.

Chaum began writing mathematical formulas on the paper.

Suppose a user has a message m, and they want the bank to sign m without the bank knowing what m is. The user can choose a random number r, compute m' = m × r^e mod n (where e and n are the bank's public key parameters), and then send m' to the bank.

The bank uses its private key d to sign m', getting s' = (m')^d mod n, and then returns it to the user.

The user now computes s = s' × r^(-1) mod n.

s = s' × r^(-1) = (m')^d × r^(-1) = (m × r^e)^d × r^(-1) = m^d × r^(ed) × r^(-1) = m^d × r × r^(-1) = m^d mod n.

"This is the bank's signature!" Chaum nearly shouted.

Because of the properties of RSA, e×d ≡ 1 mod φ(n), so r^(ed) ≡ r mod n. Through this method, the user obtains the bank's valid signature s = m^d mod n on the original message m, but the bank only saw the blinded message m' and could not know it was actually signing m.

Chaum set down his pencil, leaned back in his chair, his heart pounding like a drum.

This was what he had been searching for — the blind signature.

He immediately recognized the revolutionary significance of this technique. If applied to electronic payments, users could have the bank blindly sign a random serial number representing currency, thereby obtaining a "digital banknote" that the bank could not trace. When the user spent this banknote, merchants could verify its authenticity (because it bore the bank's signature), but the bank could not know who the banknote was originally issued to, nor who now holds it.

"True anonymous electronic cash," Chaum said softly. "No institution can monitor it, no government can trace it, just like real cash."

He spent the following months perfecting this idea, proving its security, and designing a complete protocol flow. In the summer of 1982, he first publicly introduced the concept of blind signatures at a cryptography conference.

The audience's reaction was mixed.

Some praised the mathematical elegance of the technique, calling it "an important extension of public-key cryptography." Others expressed skepticism about its practicality — the computational cost was too high, the protocol too complex, ordinary people could barely understand it.

But there was another reaction that unsettled Chaum.

"Do you realize what this will be used for?" a government representative asked him privately after the session. "Money laundering, tax evasion, funding crime — you are providing tools for criminals."

Chaum looked directly into the man's eyes and replied calmly: "Technology is neutral, sir. The telephone can be used by criminals, but we also use it to communicate. Cars can be used for fleeing, but we also use them for transportation. What matters is whether the benefits of technology outweigh the risks. And I firmly believe that protecting ordinary people's right to privacy is the most fundamental value of any society."

The government representative shook his head and walked away, but Chaum knew this was only the beginning. He had touched a sensitive nerve — governments and financial institutions were unwilling to relinquish their power to monitor the flow of funds, and electronic cash threatened precisely that power.

### 3. The Doctoral Dissertation: A Manifesto for Cryptography

In 1982, Chaum completed his doctoral dissertation, titled "Computer Systems Established, Maintained, and Trusted by Mutually Suspicious Groups."

It was a concise but profoundly influential paper. In it, Chaum systematically expounded the mathematical principles of blind signatures and described in detail an anonymous electronic payment system based on blind signatures — essentially the prototype of electronic cash.

"This dissertation is not merely a technical demonstration," Chaum wrote in its introduction. "It is a prophecy for the future. In the not-too-distant future, our society will become increasingly digital. Every transaction, every communication, every action will leave an electronic trace. If we do not design mechanisms for protecting privacy now, there will be no privacy in the future."

He painted a troubling vision in the dissertation:

"Imagine walking into a store and purchasing a product electronically. Detailed information about that transaction — what you bought, when you bought it, how much you spent — will all be recorded in some database. This information can be used by merchants to analyze your spending habits, by governments to monitor your behavior, by hackers to extort you. Worse still, these records will exist forever. You cannot delete them; you cannot control them."

"But with anonymous electronic cash," he continued, "the situation would be entirely different. You could walk into a store, complete payment, and leave, just as you would with real cash. No records, no tracking, no surveillance. You regain control over your own information."

The dissertation attracted some attention in academia, but more in the form of skepticism and criticism.

Some economists questioned the viability of anonymous currency — without tracing capabilities, how could fraud be prevented? How could taxes be collected? How could laws be enforced?

Some computer scientists questioned the practicality of the technology — the computational cost of blind signatures was too high to support large-scale payment systems; key management was too complex for ordinary users to handle safely.

Others criticized it from a moral standpoint — anonymity would protect criminals, weaken the government's governance capacity, and lead to social disorder.

Chaum responded to these criticisms carefully. In subsequent papers, he pointed out that anonymity and accountability were not contradictory — a system could be designed to protect user privacy under normal circumstances while revealing identity under specific conditions (such as a court order). He also emphasized that electronic cash designs could include various regulatory mechanisms, such as limits on single transaction amounts or identity verification requirements for large transactions.

"I am not advocating anarchism," he wrote in a response article. "I believe in the importance of law and order. But I also believe that privacy is the cornerstone of a democratic society. If a citizen cannot even keep their own economic behavior confidential, what freedom can they speak of?"

Despite the criticisms, Chaum's work gradually gained recognition from some quarters. In 1983, he was invited to speak at several international conferences, his papers were cited increasingly often, and some cryptographers began following up on research into extended applications of blind signatures.

More importantly, he began attracting like-minded followers.

"I remember the feeling when I first heard Chaum speak," a young cryptographer recalled later. "He stood at the podium, his eyes sparkling, his hands gesturing animatedly as he talked. He said that cryptography could be a tool for freedom, that it could protect ordinary people from surveillance by big corporations and governments. At that moment, I felt I had found my calling."

This young cryptographer was Tim May, who would later become one of the central figures of the Cypherpunk movement. May and Chaum met at a cryptography conference in 1983, and they hit it off immediately, often discussing cryptography, privacy, and the future of society together.

"Chaum was a true idealist," May wrote later. "He believed that technology could change the world, that mathematics could defend freedom. In that era, that kind of idealism was rare and precious."

### 4. Years in the Netherlands: The Ideal Kingdom at CWI

In 1983, the same year Chaum completed his doctoral dissertation, he received an invitation from Europe.

The Centrum Wiskunde & Informatica (CWI), located in Amsterdam, was one of the most important computer science research centers in Europe at the time. Its director, having heard about Chaum's work on blind signatures and anonymous payments, invited him to join the institute as a senior researcher.

"It was a difficult decision," Chaum recalled later. "I had already built my academic network at Berkeley; my family and friends were all in America. But CWI offered an ideal environment — ample funding, excellent colleagues, and a stronger European cultural respect for privacy protection."

In early 1984, Chaum moved to Amsterdam.

The city captivated him immediately. The ancient buildings along the canals, the aroma of tobacco drifting from corner cafes, the Rembrandts and Van Goghs hanging in the museums, and that unique, relaxed yet intellectually vibrant atmosphere — everything made him feel right at home.

"Amsterdam is a city that believes in freedom," Chaum said. "It has a tradition of tolerance and openness, a deep respect for individual privacy. Here, I felt my ideals had found fertile ground."

CWI provided him with a spacious office equipped with state-of-the-art facilities. More importantly, CWI gave him freedom — freedom in academic direction, freedom in research time, freedom in team collaboration.

Chaum began assembling his own research team. He recruited a group of young cryptographers and computer scientists, including Stefan Brands, Bert den Boer, and others. They worked together, ate together, and discussed the future of cryptography in Amsterdam's bars.

"Those were wonderful times," Brands recalled later. "Chaum was a man of great passion. He could speak for hours on end in conference rooms, filling blackboards with formulas and diagrams, explaining his vision. Sometimes we would argue late into the night, debating protocol details, security proofs, the challenges of practical application. But even in the most heated arguments, you could feel his love for the cause."

During his years at CWI, Chaum pushed his theories to new heights. He was not satisfied with the basic form of blind signatures; he began designing more complex and powerful cryptographic protocols.

He proposed the concept of "untraceable credentials" — a system that allows users to prove they possess a certain qualification (such as being of age, having a degree, or holding a membership) without revealing who they are.

"Imagine," Chaum explained in a lecture, "you want to access an adult website and prove you are over 18. Under existing systems, you would need to provide ID or credit card information, which means revealing a large amount of sensitive information — your real name, address, date of birth, and more. But with untraceable credentials, you only need to provide a mathematical proof that some authority has certified you are over 18, without revealing any other information."

This technology later came to be known as "zero-knowledge proof," one of the most important breakthroughs in cryptography. In the 1990s, Shafi Goldwasser, Silvio Micali, and Charles Rackoff received the Turing Award for their pioneering work in this field.

Chaum also researched the problem of "digital identity." He proposed that every person should have a digital identity completely under their own control, rather than relying on identity documents issued by governments or companies.

"In the physical world, you can freely choose whom to show your ID to," he wrote. "But in the digital world, your identity is often controlled and tracked by various platforms. We need a technology that returns control of identity to individuals."

This research laid the foundation for modern digital identity and privacy protection technologies. Today, when we use various "privacy protection" features, when we use zero-knowledge proofs on blockchains, when we discuss "self-sovereign identity," we are walking the path that Chaum blazed in the 1980s.

But what Chaum cared about most was still electronic cash.

### 5. Perfecting eCash: From Theory to Practice

In the mid-1980s, Chaum began seriously contemplating how to turn electronic cash from theory into reality.

He realized that for electronic cash to truly be used, mathematical elegance alone was not enough. It had to be practical — computationally efficient, with a good user experience, capable of supporting large-scale payment scenarios.

He led a team at CWI to develop a prototype system for electronic cash. The system comprised several key components:

**Bank-side software**: responsible for issuing digital currency, verifying payments, and preventing double spending. The bank would maintain accounts for each user; users could deposit funds into their accounts through traditional methods (such as bank transfers) and then "withdraw" electronic cash.

**User-side software**: allowed users to manage their electronic cash wallets, make and receive payments. The user interface was designed to be as simple as possible — select the amount to pay, click the "pay" button, and generate an encrypted payment credential.

**Merchant-side software**: allowed merchants to accept electronic cash payments and verify payment validity in real time. Merchants could periodically "deposit" the electronic cash they received at the bank, exchanging it for traditional currency.

"We spent two years perfecting this system," Chaum recalled. "The biggest challenge was performance. Blind signatures require a large amount of computation. If every payment took several seconds to process, users wouldn't accept it. We needed to optimize algorithms, use faster hardware, and design efficient protocol flows to reduce computation."

Another challenge was the problem of "offline payments."

Early electronic payment systems (such as credit cards) required an online connection to the bank to verify transactions. This meant that without a network connection, payments could not be completed. Chaum wanted electronic cash to support offline payments — users could "download" electronic cash onto their devices and then make payments without a network connection.

"The difficulty with offline payments is double spending," Chaum explained. "If you can pay offline, you could pay the same money to two different people, and each of them would be unaware that the money had already been spent. The traditional solution is online verification, but that defeats the purpose of offline payments."

Chaum's solution was clever: he designed electronic cash as a "traceable double spender" system. Under normal circumstances, payments were completely anonymous; but if someone attempted to double spend (spend the same money twice), the system would reveal that person's identity.

"This is a deterrent mechanism," Chaum said. "Users know that if they cheat, they will be caught, so they don't cheat. But under normal circumstances, privacy is fully protected."

This technology later came to be known as "fair electronic cash," striking a balance between privacy protection and fraud prevention. Although it sacrificed some anonymity (there was theoretically a possibility of being traced), it greatly improved the system's practicality.

By the late 1980s, Chaum's team had developed a fully functional electronic cash prototype. They tested it internally at CWI, letting employees use electronic cash to purchase food at the institute's cafeteria and shop at its stores.

"The test results were very good," Chaum said proudly. "The system ran stably, user feedback was positive. People liked the convenience of the payment, and they liked knowing they weren't being tracked."

But he also knew that for electronic cash to move out of the lab and into real commercial applications, one critical thing was still needed — funding.

Developing a large-scale electronic payment system required substantial investment. Servers, software development, security audits, marketing — each required capital. CWI's academic budget was limited and could not support commercialization efforts.

Chaum needed to find investors.

### 6. The Birth and Commercial Journey of DigiCash

In 1990, Chaum partnered with Dutch businessman Robert Gallant to found DigiCash Inc. This was a significant step toward the commercialization of electronic cash.

The founding of DigiCash was a major turning point in Chaum's life. From a pure academic, he became an entrepreneur; from the laboratory to the market, from theory to practice. This transition was full of challenges, but also full of hope.

Gallant was an experienced businessman who had served as an executive at several technology companies. He saw the potential in electronic cash — not just as a technology, but as a commercial opportunity that could transform the payment industry. "This technology can change the world," Gallant told Chaum. "But we need to turn it into a product, find customers, and build a business model. That's what I'm here to do."

Chaum and Gallant divided their responsibilities clearly: Chaum handled technology, Gallant handled business. They rented a small building in the outskirts of Amsterdam, recruited over twenty engineers and cryptographers, and began intense development work.

"We all believed then that we were making history," an early employee recalled. "Dr. Chaum would tell us about his vision — a world where privacy was protected, a payment system free of surveillance. That kind of idealism was infectious; it made us feel our work had meaning."

In the company's early days, Chaum and Gallant set ambitious plans. They wanted electronic cash to become the world's dominant electronic payment method within five years, to replace credit cards, to change the world.

DigiCash first established partnerships with several Dutch local banks. These banks were willing to try the new technology as a supplement to traditional payment systems. In 1993, DigiCash launched the first commercial version of its electronic cash system, allowing users to open accounts at these banks, exchange electronic cash, and spend it at merchants that accepted electronic cash.

In 1994, DigiCash achieved its first major breakthrough. The Federal Reserve Bank of St. Louis — a key part of the U.S. central banking system — announced a partnership with DigiCash to conduct a pilot test of electronic cash.

"This was a historic moment," Chaum said excitedly. "One of the world's greatest financial power institutions had endorsed our technology. This proved that electronic cash was not just the toy of idealists — it had real potential."

The pilot project allowed Federal Reserve employees in St. Louis to use electronic cash for internal payments. The test results were very positive — the system ran stably, user satisfaction was high, and no major security issues were found.

"Our report showed that electronic cash could effectively reduce transaction costs and improve payment efficiency," a Federal Reserve official said at the pilot summary meeting. "More importantly, it demonstrated a new paradigm for digital payments — ensuring security while protecting privacy."

This success brought DigiCash increased attention. Central banks in other countries began to take note, and some commercial banks expressed interest in partnerships.

In 1995, Deutsche Bank — Germany's largest bank — announced it would become an issuing bank for electronic cash. This was DigiCash's most important commercial partnership to date.

"Deutsche Bank's involvement was a turning point," Gallant said. "It proved that the traditional financial world was beginning to take electronic cash seriously. We were no longer a fringe experiment — we were entering the mainstream."

With more banks joining, the number of electronic cash users began to grow. DigiCash conducted business in multiple European countries, and users could shop online, pay for services, and even make purchases at some physical stores using electronic cash.

But DigiCash faced serious challenges. First, there was the technical challenge — as the user base grew, performance issues with the electronic cash system began to surface. Blind signatures required heavy computation, and servers were often overwhelmed during peak hours. Payments were sometimes delayed by seconds or even minutes, frustrating users accustomed to the immediacy of credit cards.

Second, there were business challenges — banks worried about regulatory risks, and governments were skeptical of anonymous payments. The Financial Crimes Enforcement Network (FinCEN), a bureau of the U.S. Department of the Treasury, published reports warning that anonymous electronic cash could be used for money laundering and other illegal activities.

And the biggest challenge was user adoption — ordinary users seemed not to care about privacy protection. They preferred convenient credit cards over the complexity of electronic cash. Feedback from bankers and investors left Chaum despondent: "Users don't care about privacy. They are willing to trade privacy for convenience."

### 7. The Dream Shattered by Netscape and the Fall of DigiCash

In 1996, DigiCash experienced its moment of glory, and also a turning point in its fate.

That year, DigiCash reached a partnership agreement with Netscape Communications Corporation. Netscape was the king of the internet world at the time, and its Netscape Navigator browser commanded more than 90 percent of the market share.

"Netscape wanted to build payment functionality directly into the browser," Gallant announced excitedly to the whole company. "They chose electronic cash! This means millions of Netscape users will be able to use electronic cash for online payments directly!"

The entire company was electrified. This was a game-changer opportunity — if electronic cash became the default payment method in Netscape Navigator, DigiCash would instantly gain a massive user base and become the standard for online payments.

Chaum and his team worked around the clock, developing Netscape browser plugins and optimizing the electronic cash integration experience. Netscape also sent engineering teams to collaborate closely with DigiCash.

But fate played a cruel trick.

At the end of 1996, just before electronic cash was about to be integrated into the Netscape browser, Netscape suddenly announced it was canceling the partnership.

"Netscape gave us no clear explanation," Gallant said angrily. "They just said it was a 'strategic repositioning.' But we all knew what really happened — Microsoft Corporation applied pressure."

Microsoft was at the time全力 promoting its IE browser (Internet Explorer), trying to defeat Netscape. As part of its competitive strategy, Microsoft exerted enormous pressure on Netscape — if Netscape integrated a new technology that might threaten the traditional financial system, Microsoft would raise concerns before regulators.

"Netscape caved," Chaum said bitterly. "They chose safety over innovation. I understand their decision — they were facing an existential threat and couldn't take additional risks. But for us, it was a fatal blow."

With the Netscape opportunity lost, DigiCash's prospects grew dim. Fundraising became more difficult, some employees began to leave, and partners' confidence wavered.

In 1997, Deutsche Bank announced it would gradually reduce its support for the electronic cash project. The official reason was "strategic repositioning," but privately, bank executives revealed that regulators had applied enormous pressure. Other banks followed suit, withdrawing their partnership agreements with DigiCash.

"We were isolated," Chaum said. "The banking system is a tightly knit network. If mainstream banks don't accept you, you're shut out. Without bank support, electronic cash couldn't be issued, users couldn't deposit funds, and the entire system ground to a halt."

In 1998, DigiCash formally filed for bankruptcy protection. David Chaum's idealistic experiment had ended in failure.

"That was the darkest period of my life," Chaum recalled later. "I fell into a deep depression. I began questioning everything — my beliefs, my work, my worth. If the world doesn't need what I have to offer, what meaning does my existence have?"

But the seeds Chaum had planted did not die with DigiCash's bankruptcy. Quite the opposite — they took root in every corner of cyberspace, waiting for the right moment to sprout anew.

"We were too early," Chaum reflected later. "The problems we were trying to solve weren't yet real problems. People hadn't yet recognized the importance of privacy, hadn't yet felt the dangers of centralized systems. By the time these problems truly erupted, many years had already passed."

---

## Part Two: The Pioneers of Digital Gold

The failure of DigiCash was not the end of the digital currency story. Quite the opposite — it marked the beginning of a new chapter.

In the late 1990s and early 2000s, a group of cryptographers, programmers, and idealists scattered across the globe continued exploring the possibilities of digital currency from different corners. They exchanged ideas online, shared code, and debated how cryptography could be used to protect individual freedom and resist government surveillance.

They were the Cypherpunks — a loose alliance of cryptography enthusiasts, libertarians, and privacy advocates. They believed that through technology, individuals could regain control over their own lives.

"The failure of DigiCash was a heavy blow to us," a Cypherpunk member recalled later. "Chaum was our hero, electronic cash was our hope. But when DigiCash went under, we realized that relying on a single company was not enough. We needed a more decentralized approach, a system that didn't depend on any single entity."

In this underground world, the ideas of three pioneers were particularly influential. They were Wei Dai, Nick Szabo, and Hal Finney.

### 1. The Cypherpunk Movement — An Underground World in the Digital Age

To understand the contributions of Wei Dai, Szabo, and Finney, one must first understand their environment — the Cypherpunk movement.

The Cypherpunk movement emerged in the early 1990s as a loose alliance of technicians sharing common interests in cryptography, privacy, and libertarianism. They exchanged ideas through mailing lists, shared code, and debated how technology could protect individual freedom.

"Cypherpunks write code," read the Cypherpunk Manifesto published in 1993. "We know that someone has to write code to defend privacy, and since we can't get privacy unless we all do, we're going to write it. We publish our code so that our fellow Cypherpunks may practice and play with it."

The core philosophy of this movement was: privacy is not secrecy, it is the power of choice. A person should have the right to choose whom to show their information to, rather than being forced to expose all information to governments and large corporations.

"In an electronic age, privacy means the ability to reveal selectively what is ours," wrote Eric Hughes, author of the manifesto. "We expect that governments and other large organizations will not get our compliance out of goodwill. We must defend our own privacy ourselves."

The Cypherpunk mailing list became the center of this underground world. Every day, programmers, cryptographers, philosophers, and economists from around the world exchanged ideas there, discussing everything from anonymous communications to digital cash.

"That mailing list was like a window into the future," a early participant recalled. "There you could see the most cutting-edge cryptographic ideas, hear the most radical political philosophies, and find like-minded companions. It was a free market of ideas."

In this underground world, the failure of DigiCash was not an ending, but a lesson. It taught Cypherpunks that relying on a centralized system controlled by a single company was unsustainable. To truly protect privacy, a completely decentralized system was needed — no company, no bank, no government that could shut it down.

"We need a system like cash," Tim May wrote on the mailing list. "But not issued by governments, issued by mathematics. Not controlled by banks, controlled by algorithms."

This vision sounded like science fiction, but to the Cypherpunks it seemed entirely achievable. The technology already existed; someone just needed to put the pieces together.

### 2. Wei Dai and b-money — Pioneer of Distributed Ledger

If Chaum was the light in the field of digital currency, then Wei Dai was the shadow quietly toiling in the darkness.

To this day, Wei Dai's true identity remains a mystery. The only thing that can be confirmed is that he is an extraordinarily brilliant cryptographer with a deep understanding of both distributed systems and economics.

Wei Dai was a low-profile and mysterious presence in the Cypherpunk community. He rarely attended offline gatherings, never disclosed personal information, and had never even published a photograph of himself. But his ideas spread through the mailing list and influenced countless people.

In 1998, the same year DigiCash went bankrupt, Wei Dai posted a brief paper on the Cypherpunk mailing list. The paper was only a few thousand words, with an unassuming title: "b-money, an anonymous, distributed electronic cash system."

But in this brief paper, he proposed a revolutionary idea: decentralized ledger-keeping.

In Chaum's electronic cash system, the bank still played a centralized role — though the bank didn't know where the money was spent, it was still the issuer of currency and the authority on signatures. If the bank went bankrupt or was shut down by the government, the entire system would collapse.

Wei Dai asked: why not distribute the ledger-keeping function to every participant in the network?

"In a world without central authority," Wei Dai wrote, "the community must enforce the rules itself. Everyone maintains a database recording who owns how much money. When someone wants to transfer funds, they broadcast a message and everyone updates their own database."

This idea seemed very intuitive, but it had a fatal difficulty in implementation: how to prevent double spending? If someone simultaneously sent the same money to two different people, how would the network decide which transaction was valid? Without a centralized authority, who had the power to make that decision?

Wei Dai proposed a solution. He suggested that the community vote on which transactions were valid, with the weight of each participant's vote proportional to their computational investment.

"The problem with this scheme is that it cannot withstand a Sybil attack," a cryptographer later analyzed. "An attacker could create countless false identities to gain voting rights. But Wei Dai's core insight — the possibility of decentralized consensus — was correct."

Wei Dai also proposed another innovative idea: value anchoring. He realized that a digital currency with no intrinsic value might face severe volatility. He proposed a mechanism that would tie b-money's value to a basket of goods and services, thereby maintaining relative stability.

"The value of currency comes from the goods it can purchase," he wrote. "If b-money can consistently be exchanged for a certain amount of computing resources, storage space, and bandwidth, it will have an intrinsic value foundation."

The b-money proposal generated some discussion in the cryptography community, but ultimately did not develop into an actual project. For the internet of 1998, b-money's technical requirements were too demanding — it required a fully decentralized network with every participant running complex software, which was impractical in the era of dial-up modems.

But the seeds of b-money had been sown. The concept of "decentralized ledger-keeping" that Wei Dai proposed would become one of the core theoretical foundations for Satoshi Nakamoto's invention of Bitcoin a decade later.

### 3. Nick Szabo and Bit Gold — Founder of Proof-of-Work

If Wei Dai was a hermit in the history of digital currency, then Nick Szabo was a more active missionary.

Nick Szabo was a man of many identities. He was a cryptographer, a legal scholar, a programmer, and an economist. He earned his degree in computer science from the University of Washington, then pursued law at George Washington University. This interdisciplinary background enabled him to approach the problem of digital currency from a unique perspective.

Szabo's interest in digital currency dated back to the early 1990s. He was a core member of the Cypherpunk movement, publishing extensively on the mailing list about digital cash, smart contracts, law, and technology. Beyond digital currency, Szabo also coined the concept of "smart contracts" — automatically executing digital agreements that require no intermediary involvement.

In 2005, Szabo published a blog article titled "Bit Gold," which described his vision for digital currency in detail.

Bit Gold's design incorporated the strengths of both b-money and Hashcash (a proof-of-work system for preventing spam, proposed by Adam Back in 1997), attempting to create a digital currency that was both intrinsically valuable and completely decentralized.

Bit Gold's core mechanisms were as follows:

**Proof-of-Work**: Participants "mined" Bit Gold by solving computational puzzles. These puzzles required substantial computational resources to solve but were easy to verify once solved.

**Timestamping**: The results of solved puzzles needed to be timestamped, proving they were solved at a specific point in time. Szabo proposed using distributed timestamp servers to record these proofs.

**Value Accumulation**: Bit Gold's value came from the computational resources consumed in solving the puzzles. This was analogous to the cost of mining gold — gold has value partly because acquiring it requires the expenditure of labor and resources.

**Ownership Transfer**: Bit Gold ownership was transferred through cryptographic signatures. The owner signed a message with their private key, declaring the transfer of ownership to another person.

"Bit Gold solves several core problems of digital currency," Szabo wrote. "It is decentralized, relying on no central authority. It has intrinsic value, because acquiring it requires the consumption of real resources. It is secure, because forging it requires solving the same computational puzzles."

Bit Gold's design was already very close to what Bitcoin would later become. It introduced proof-of-work as a mechanism for value anchoring and security, proposed the concept of decentralized timestamping, and designed a cryptography-based ownership transfer system.

But Bit Gold also had a fatal flaw: it did not solve the double-spending problem.

"I could not find a completely decentralized method to prevent double spending," Szabo recalled later. "This problem troubled me for a long time. I knew the solution was right in front of me, but I couldn't reach it."

Bit Gold was never implemented. But Bit Gold's intellectual legacy was immense. When Satoshi Nakamoto published the Bitcoin whitepaper in 2008, many cryptographers immediately noted the similarities between Bitcoin and Bit Gold.

"Bitcoin achieved most of the goals we dreamed of during the Cypherpunk era," Szabo said in a 2011 interview. "It was the crystallization of our twenty years of exploration. Though I might have chosen some design details differently, Satoshi solved the critical problem that none of us could solve. That was a true breakthrough."

### 4. Hal Finney and RPOW — Pioneer of Reusable Proof-of-Work

In the exploration of digital currency before Bitcoin, there is one more figure who deserves special attention: Hal Finney.

Finney was a legendary figure in the cryptography community. He graduated from the California Institute of Technology with an engineering degree and then joined Phil Zimmermann's team to help develop PGP (Pretty Good Privacy) — the world's first widely used public-key encryption software.

PGP was released in 1991, giving ordinary people access to military-grade encryption technology for protecting their communications. The U.S. government imposed export controls on PGP, classifying it as a "munition," and Zimmermann faced criminal prosecution. Finney and other volunteers bypassed export controls by printing the PGP source code in books (protected by the First Amendment), making the technology available to users worldwide.

"PGP was the first major victory of the Cypherpunk movement," a Cypherpunk recalled. "It proved that technology could defeat government control, that ordinary people could use military-grade encryption. Finney's contributions to this project were enormous."

Finney's interest in digital currency was long-standing. As a core member of the Cypherpunk movement, he had always followed developments in electronic cash, b-money, and Bit Gold. But he was not just a theorist — he was a practitioner, a programmer who loved turning ideas into code.

In 2004, Finney created the RPOW (Reusable Proofs of Work) system. RPOW was the first actual system to implement reusable proof-of-work currency.

RPOW's core innovation was "reusability." In the original Hashcash, a proof could only be used once, serving as evidence that the sender had expended computational effort (thereby preventing spam). Finney designed a mechanism that allowed Hashcash proofs to be "converted" into RPOW tokens, which could then be transferred and reused like currency.

"RPOW tokens represent a right to computational resources," Finney wrote. "When you hold RPOW, you are actually holding proof of computational work already expended by someone else (or yourself). It's like a digital version of gold — gold has value because acquiring it requires the expenditure of labor and resources."

The RPOW system included a key component: the RPOW server. This server was responsible for verifying proofs of work, issuing RPOW tokens, and recording ownership transfers. Although the server was centralized, Finney designed security mechanisms ensuring the server could neither forge tokens nor steal users' assets.

Though RPOW achieved a technical breakthrough, it still relied on a centralized server. If the server was shut down or tampered with, the entire system would collapse. This limitation prevented RPOW from becoming a truly decentralized digital currency, but it demonstrated the viability of proof-of-work as a foundation for digital currency.

"RPOW was an important proof of concept," a cryptographer later评价. "It proved that proof-of-work could serve as a mechanism for value storage and transfer. This paved the way for the birth of Bitcoin."

Finney later became one of Bitcoin's earliest participants. In January 2009, when Satoshi Nakamoto released the first version of Bitcoin software, Finney was the first person to download and run it. He participated in Bitcoin's first transaction — Satoshi sent him 10 bitcoins, the first transfer in Bitcoin's history.

"When I ran the Bitcoin software, it worked like magic," Finney recalled later. "I mined some blocks, Satoshi sent me some coins, I sent some back to him. Everything ran as designed. I knew this was a historic moment."

In 2014, Finney passed away at the age of 58. In his final moments, he was diagnosed with Amyotrophic Lateral Sclerosis (ALS). His family revealed that Finney had stored his bitcoins in cold storage, earmarked for future ALS research funding.

Finney's passing was an enormous loss to the cryptography community, but his legacy — the RPOW system, his contributions to PGP, his role as one of Bitcoin's earliest supporters — will be forever remembered.

### 5. The Spiritual Legacy of the Cypherpunk Underground

Wei Dai, Nick Szabo, and Hal Finney — these three pioneers represented the core spirit of the Cypherpunk movement.

They did not believe in authority, did not believe in central institutions. They believed that mathematics and cryptography could build a new social order. They did not care for fame or fortune; their single pursuit was using technology to protect individual freedom.

"Cypherpunks write code," Eric Hughes wrote. "We know that someone has to write code to defend privacy, and since we can't get privacy unless we all do, we're going to write it. We publish our code so that our fellow Cypherpunks may practice and play with it."

This underground world had no clear organizational structure, no leader, no membership list. It had only a mailing list — a virtual space for exchange where cryptographers, programmers, philosophers, and economists from around the world freely shared ideas.

"That mailing list was an important part of my life," a early participant recalled. "Every day I would receive dozens of emails discussing all sorts of ideas — anonymous communications, digital cash, smart contracts, decentralized organizations. Many of those ideas were never realized, but that atmosphere of freedom, that passion for believing technology could change the world, was the most important experience of my life."

In this underground world, the failure of DigiCash was not an ending, but a lesson. It taught Cypherpunks that relying on a centralized system controlled by a single company was unsustainable. To truly protect privacy, a completely decentralized system was needed — no company, no bank, no government that could shut it down.

"We need a system like cash," Tim May wrote on the mailing list. "But not issued by governments, issued by mathematics. Not controlled by banks, controlled by algorithms."

"I knew that someday someone would do it," Wei Dai recalled later. "I just didn't know who it would be or when. But when Bitcoin appeared, I immediately realized — this was it."

---

## Part Three: The Eternal Flame

### 1. David Chaum's Years of Silence

In the years following DigiCash's bankruptcy, David Chaum gradually faded from public view.

He returned to CWI to continue his academic research, but no longer with the high profile of his earlier years. He stopped talking about electronic money, stopped attending related conferences, stopped responding to media interview requests.

"He just disappeared," a cryptography colleague said. "We knew he was still at CWI, but he stopped publishing papers, stopped giving lectures, stopped participating in community discussions. The failure of DigiCash had hit him too hard."

But Chaum had not stopped thinking. He had simply chosen silence.

During those silent years, he continued researching cryptography, but turned to other areas — voting systems, digital identity, security protocols. His work was still excellent, he still published high-quality papers, but he never mentioned electronic cash, never spoke of the dream of digital currency.

When Satoshi Nakamoto published the Bitcoin whitepaper in 2008, Chaum was among the first to read it.

He sat at his computer, reading the nine-page paper word by word. When he reached the section on blockchain and proof-of-work, his hands began to tremble.

"This is the answer," he murmured, his eyes glistening with tears. "This is the answer I was searching for back then. Decentralized, no banks, no government — just mathematics and cryptography. Satoshi did what I couldn't do."

"Should I feel jealous?" he asked himself. "After all, this was the lifelong goal I pursued, and I failed. Now someone has succeeded — should I feel bitter?"

But he did not feel jealous. Instead, he felt profound relief.

"No, I am not jealous. I am happy. Because my dream has finally been realized, even if not through my own hands. Digital cash may have failed, but the idea survived. Satoshi stood on the shoulders of me and others and created this miracle. This is the transmission of knowledge. This is the advancement of science."

### 2. The Relay of the Pioneers

History is a relay race.

David Chaum ran his leg. He lit the torch. Though his digital cash ultimately failed, he proved that anonymous digital payments were possible. He brought blind signatures, zero-knowledge proofs, and anonymous credentials into the world, laying the theoretical foundation for future explorers.

Wei Dai took the torch. He proposed the concept of b-money, first systematically articulating the possibility of decentralized ledger-keeping. Though b-money was never implemented, his ideas — distributed ledgers, community consensus, value anchoring — would become core theoretical foundations for Bitcoin.

Nick Szabo took the torch. He designed Bit Gold, introducing proof-of-work as the value foundation and security mechanism for digital currency. Though he failed to solve the double-spending problem, he pointed the way — using computational resources to mint digital gold.

Hal Finney took the torch. He implemented the RPOW system, demonstrating the viability of proof-of-work currency. He became one of Bitcoin's earliest participants, witnessing the arrival of that historic moment.

Each leg had its limitations, each leg had its failures, but each leg pushed forward one step further.

### 3. Satoshi Nakamoto's Jigsaw Puzzle

In 2008, a person operating under the pseudonym Satoshi Nakamoto placed the final piece of the puzzle.

It was an autumn, and the global financial crisis was raging. Lehman Brothers had collapsed, stock markets were plummeting, and public trust in the traditional financial system had hit rock bottom. In this particular moment, Satoshi published his whitepaper.

This was no coincidence. Satoshi embedded a message in the Genesis Block: "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks." This message clearly expressed his motivation — to create a currency free from the control of governments and banks.

Satoshi did not create Bitcoin from thin air. He stood on the shoulders of giants, integrating the work of all the pioneers:

- From David Chaum, he inherited the idea of using cryptography to protect privacy;
- From Wei Dai, he borrowed the concept of decentralized ledger-keeping;
- From Nick Szabo, he introduced the proof-of-work mechanism;
- From Hal Finney, he learned the practice of reusable proofs of work.

Then he solved the problem that had haunted everyone for years: the double-spending problem.

Satoshi's solution was genius — the blockchain. Through a distributed timestamping server (later known as the miner network), all transactions were recorded in a public ledger, linked in chronological order into a chain. To tamper with a transaction, an attacker would have to recalculate the proof-of-work for every block after that transaction — computationally impossible.

"Innovation is never the achievement of one person," Chaum said in a later interview. "It is the cumulative result of countless people's efforts. I stood on the shoulders of giants, and Satoshi stood on my shoulders. This is the transmission of knowledge. This is how humanity advances."

On October 31, 2008, Satoshi published the Bitcoin whitepaper on the cryptography mailing list. At that moment, all the pioneers knew — history had been rewritten.

### 4. The Enduring Value of Pioneer Spirit

Looking back on this history, we cannot help but ask: What were these pioneers pursuing? Why did they devote their lives to chasing a dream that seemed impossible to realize?

The answer perhaps lies in their understanding of freedom.

To David Chaum, privacy was the foundation of freedom. Without privacy, there is no true freedom. In a society of complete transparency, people dare not express genuine thoughts, dare not pursue lifestyles different from the norm, dare not challenge established authority. Privacy gives people the space to make mistakes, the opportunity to grow, the possibility to maintain independent personalities.

To Wei Dai, decentralization was the guarantor of freedom. Centralization means the concentration of power, and power always tends toward corruption. Only decentralized systems can prevent the abuse of power, ensuring that everyone participates equally.

To Nick Szabo, code is law. Smart contracts make rules transparent and immutable, eliminating human bias and corruption. This is a higher form of justice, a fairness guaranteed by mathematics.

To Hal Finney, technology is the extension of humanity. Through cryptography, ordinary people can gain the ability to stand up to powerful institutions. This is the power of technological democratization — equal rights in the digital age.

These ideas retain profound meaning today.

When we discuss data privacy, we are discussing Chaum's ideas. When we discuss Decentralized Finance (DeFi), we are discussing Szabo's smart contracts. When we discuss Bitcoin's decentralization, we are discussing Dai's vision.

### 5. The Eternal Transmission of the Flame

Today, looking back from the 2020s to that night in 1983, we can see a complete picture.

We see a young researcher, in a dim basement, lighting a torch. That flame was once so weak it nearly went out, but it ultimately illuminated the entire world.

David Chaum may not have seen the complete realization of his dream. DigiCash went bankrupt, electronic cash was forgotten, he failed commercially. Wei Dai, Nick Szabo, Hal Finney — these pioneers did not gain wealth or fame for their contributions.

But the seeds they planted ultimately grew into towering trees.

"Innovation is like the lonely howl of a wolf," Chaum wrote in his diary. "It is often born through perseverance, yet strangled by the iron chains of reality. But the flame of dreams will ultimately ignite the eternal stars."

This is the fate of pioneers. They walk through darkness, unable to see the end, not knowing whether their efforts will bear fruit. But they press on, because they believe that even if they cannot see the light themselves, their work will light the way for those who come after.

### 6. The Legacy and Lessons of the Pioneers

Looking back on the stories of these pioneers, we can draw many valuable lessons.

The first is about the relationship between ideals and reality. The story of Chaum, electronic cash, and DigiCash tells us that ideals are beautiful, but reality is complex. A good idea needs technological support, market acceptance, and regulatory cooperation — all indispensable. Idealists often overlook the constraints of reality, while realists often lack the courage to change the world. Successful innovators need to find balance between the two.

The second is about the value of failure. From electronic cash to b-money, from Bit Gold to RPOW, all these projects failed — at least from the perspective of commercial success. But their failures accumulated valuable experience, indicated which paths were dead ends, and paved the way for later successes. Without these failures, there would have been no Bitcoin.

The third is about the transmission of knowledge. The development of science and technology is a continuous process; every breakthrough builds on the foundation of those who came before. Satoshi Nakamoto was not a lone genius — he was an inheritor standing on the shoulders of giants. It was precisely because of the work of Chaum, Dai, Szabo, Finney, and others that Satoshi was able to, at that specific moment, assemble all the pieces into a complete picture.

The fourth is about the interaction between technology and society. Technology never exists in isolation; it is deeply embedded in social structures. The failure of electronic cash was largely because society at the time was not yet ready to accept it — the internet had not yet become sufficiently widespread, cryptography technology was not yet mature enough, the regulatory environment was not yet favorable, and the public had not yet placed a high enough value on privacy. Bitcoin's success came because it was born at a more opportune moment.

The last is about the spirit of the pioneers. These pioneers shared a common trait: they did not struggle for wealth or fame, but for belief. They believed that technology could change the world, that mathematics could defend freedom, that individuals should have control over their own data. This kind of pure idealism is especially precious in today's highly commercialized world.

"What we do may not see results in our generation," Hal Finney said in a生前 interview. "But that's okay. What's important is that we have paved the way for the future. Someday, when digital currency becomes mainstream, when people can truly control their own financial privacy, we will know that our efforts were not in vain."

### 7. From Pioneers to the Mainstream — The Long Journey of Digital Currency

From Chaum's invention of blind signatures in 1983 to Satoshi Nakamoto's publication of the Bitcoin whitepaper in 2008, twenty-five years passed. During those twenty-five years, digital currency gradually evolved from a purely theoretical concept into a viable technological solution.

But this was only the beginning of a long journey.

From 2008 to today, another decade and more have passed. In these years, Bitcoin has evolved from a geek's toy into a globally noticed financial asset; blockchain technology has evolved from the underlying technology of Bitcoin into a general-purpose technology that may transform multiple industries; digital currency has shifted from a fringe concept into the subject of study by central banks around the world.

This process has been full of ups and downs. There was the madness of the 2017 Initial Coin Offering (ICO) boom and the pain of the 2018 market crash. There was the innovative explosion of the 2020 DeFi summer and the trust crisis of 2022 when various projects went bankrupt. But in any case, digital currency has irreversibly become an important part of our era.

"We are in the early stages of a monetary revolution," an economist wrote. "The impact of this revolution may be comparable to the invention of printing, the Industrial Revolution, or the birth of the internet. It changes not just how we pay, but the entire infrastructure of the economic system."

In this grand historical progression, the contributions of pioneers like Chaum, Dai, Szabo, and Finney will be forever remembered. They were the ones who lit the torch, who searched for paths in the darkness, who paved the way for those who came after.

When we today easily transfer money with Bitcoin, discuss the various applications of DeFi, or debate the pros and cons of Central Bank Digital Currency (CBDC), let us not forget those pioneers who worked silently in basements, debated fiercely on mailing lists, and persevered through failure.

It is because of them that we can stand here and see the world illuminated by that torch.

---

Chapter 1 End

---

## Editor's Afterword: The Pioneers — Then and Now

From Chaum's invention of blind signatures in 1983 to today, more than forty years have passed. Where are the pioneers who once lit the torch now?

After experiencing DigiCash's failure and years of silence, David Chaum returned to the frontiers of cryptography. His latest work is a new anonymous payment system known as the "xx network." This time, he brings new technologies — quantum-resistant cryptography, more efficient consensus mechanisms. History seems to be repeating, but this time, the world is ready.

Wei Dai still maintains his mystique and low profile. It is said he works on artificial intelligence research at a major technology company and rarely appears in public. But his idea of b-money has been realized through Bitcoin.

Nick Szabo continues his writing and thinking. His blog remains an important reference in the fields of cryptography and smart contracts, and his insights on blockchain technology and decentralized governance are far-reaching. Though Bit Gold was never implemented, his ideas have found expression in projects like Ethereum. Smart contracts — a concept he coined — have become the cornerstone of the blockchain world.

Hal Finney has been gone from us for a decade. But his spirit lives on. In every corner of the Bitcoin community, people commemorate this earliest participant. His transaction — the 10 bitcoins Satoshi sent him — is regarded as a sacred relic in the history of digital currency. His optimism, his passion for technology, his pursuit of freedom will forever inspire those who come after.

The pioneers' stories tell us that changing the world takes time. An idea may take decades from conception to realization; an ideal may take generations to go from being ridiculed to being accepted. But what matters is perseverance — continuing forward even when the end is not in sight.

"We are working for the future," Finney said during his lifetime. "Not for today, not for tomorrow, but for the world ten or twenty years from now. That is the mission of the pioneer."

---

Key Figures and Technologies Covered in This Chapter:

- **David Chaum**: Invented blind signature technology in 1983, laying the foundation for anonymous electronic cash. His company DigiCash went bankrupt in 1998.

- **Blind Signature**: A cryptographic technique that allows a signer to sign a message without knowing its content.

- **Wei Dai**: Proposed b-money in 1998, first systematically articulating the concept of decentralized ledger-keeping.

- **Nick Szabo**: Proposed Bit Gold in 2005, introducing the proof-of-work mechanism and coining the concept of smart contracts.

- **Proof-of-Work (PoW)**: A mechanism that proves the expenditure of computational resources, used in Bitcoin mining and blockchain security.

- **Hal Finney**: Created the RPOW system in 2004, one of Bitcoin's earliest participants, passed away in 2014 from ALS.

- **Satoshi Nakamoto**: Published the Bitcoin whitepaper in 2008, invented blockchain technology, solved the double-spending problem.

- **Blockchain**: A distributed ledger technology that ensures data immutability through cryptography and consensus mechanisms.

- **Cypherpunk**: A technological movement that emerged in the 1990s, advocating the use of cryptography to protect individual privacy and freedom.

- **CWI (Centrum Wiskunde & Informatica)**: A top computer science research institution in the Netherlands, where Chaum once worked.

- **PGP (Pretty Good Privacy)**: Public-key encryption software developed by Phil Zimmermann, with contributions from Finney.

- **DeFi (Decentralized Finance)**: Financial services built on blockchain that operate without traditional intermediaries.

- **ICO (Initial Coin Offering)**: A method of fundraising for blockchain projects through token issuance.

- **CBDC (Central Bank Digital Currency)**: Digital currency issued by a nation's central bank.

---

Word count: approximately 45,000 characters