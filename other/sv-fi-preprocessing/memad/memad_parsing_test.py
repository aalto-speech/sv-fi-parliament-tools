import unittest
from memad_parsing import Token, split_line, is_time_token, is_speaker_token, is_special_token, gather_utts

class test_split_line(unittest.TestCase):

    def test_correct_amount_of_tokens(self):
        line = ' [<puhuja_FreddiWahlström>] Håller ni lapparna lite till så får tittarna också se hur de röstar. [<0:03:48.9>]'
        tokens = split_line(line)
        self.assertEqual(len(tokens), 3)

    def test_no_padding_in_tokens(self):
        line = ' [<puhuja_FreddiWahlström>] Håller ni lapparna lite till så får tittarna också se hur de röstar. [<0:03:48.9>]'
        tokens = split_line(line)
        for token in tokens:
            self.assertEqual(token.strip(), token)

    def test_returns_correct_tokens(self):
        line = ' [<puhuja_FreddiWahlström>] Håller ni lapparna lite till så får tittarna också se hur de röstar. [<0:03:48.9>]'
        tokens = split_line(line)
        self.assertEqual(tokens[0], '[<puhuja_FreddiWahlström>]')
        self.assertEqual(tokens[1], 'Håller ni lapparna lite till så får tittarna också se hur de röstar.')
        self.assertEqual(tokens[2], '[<0:03:48.9>]')

    def test_returns_special_tokens(self):
        line = '[<puhuja_IngemoLindroos>] Va svarar din partikamrat Alexander Stubb? [<0:06:45.6>][päällekkäistä puhetta][<0:06:47.4>]'
        tokens = split_line(line)
        self.assertEqual(len(tokens), 5)
        self.assertEqual(tokens[0], '[<puhuja_IngemoLindroos>]')
        self.assertEqual(tokens[1], 'Va svarar din partikamrat Alexander Stubb?')
        self.assertEqual(tokens[2], '[<0:06:45.6>]')
        self.assertEqual(tokens[3], '[päällekkäistä puhetta]')
        self.assertEqual(tokens[4], '[<0:06:47.4>]')

class test_gather_utts(unittest.TestCase):
    def test_returns_correct_utterance(self):
        t_name = 'test_transcription1'
        tokens = {}

        start_time = '[<0:11:38.8>]'
        speaker = '[<puhuja_FreddiWahlström>]'
        text = 'Vi tar först Li Andersson sen Nils Torvalds'
        end_time = '[<0:11:41.2>]'

        tokens[t_name] = [
            Token(start_time, 0),
            Token(speaker, 1),
            Token(text, 1),
            Token(end_time, 1),
        ]

        utts = gather_utts(tokens, t_name)
        self.assertEqual(len(utts), 1)
        utt = utts[0]
        self.assertEqual(utt.speaker, 'puhuja_FreddiWahlström')
        self.assertEqual(utt.text, text)
        self.assertEqual(utt.start_pos, '0:11:38.8')
        self.assertEqual(utt.end_pos, '0:11:41.2')
        self.assertEqual(utt.id, 0)
        self.assertEqual(utt.filename, t_name)

if __name__ == '__main__':
    unittest.main()