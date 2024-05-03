import re

# def format_coupon_codes(text):
#     # This regex captures 'code' followed by an optional non-space character sequence or space-separated alphanumeric sequences.
#     formatted_text = re.sub(r'(?i)(code)(next|\w*)\s*((?:\w+\s*)*)',
#                             lambda m: m.group(1) + ' ' + m.group(2) + ''.join(m.group(3).split()), text)
#     return formatted_text
# # Example usage:
# if __name__ == '__main__':
#     sample_texts = [
#         "THE OUTNET offers anup to 70% off + extra 20% off Burberry Women Fashion Salevia coupon codenext 20.",
#         "LUISAVIAROMA offers 10% off Ami Paris Fashion Salevia coupon code SPRING10.",
#         "FARFETCH offers 15% off Acne Studios Fashion Salevia code NC15FF."
#     ]
#
#     for text in sample_texts:
#         formatted_text = format_coupon_codes(text)
#         print(formatted_text)
