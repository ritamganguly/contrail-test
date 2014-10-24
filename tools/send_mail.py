from email.mime.text import MIMEText
import smtplib
import subprocess
import ConfigParser
import sys
import os

def send_mail(config_file, file_to_send, report_details):
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    report_config = ConfigParser.ConfigParser()
    report_config.read(report_details)
    distro_sku = report_config.read('Test','Distro_Sku')
    smtpServer = config.get('Mail', 'server')
    smtpPort = config.get('Mail', 'port')
    mailSender = config.get('Mail', 'mailSender')
    mailTo = config.get('Mail', 'mailTo')
    if 'EMAIL_SUBJECT' in os.environ:
        logScenario = os.environ.get('EMAIL_SUBJECT')
    else:
        logScenario = config.get('Basic','logScenario')

    if not mailTo:
        print 'Mail destination not configured. Skipping'
        return True
    fp = open(file_to_send, 'rb')
    msg = MIMEText(fp.read(), 'html')
    fp.close()

    msg['Subject'] = '[Build %s] ' % (
         distro_sku) + logScenario + ' Report'
    msg['From'] = mailSender
    msg['To'] = mailTo

    s = None
    try: 
        s = smtplib.SMTP(smtpServer, smtpPort)
    except Exception, e:
        print "Unable to connect to Mail Server"
        return False
    s.ehlo()
    try:
        s.sendmail(mailSender, [mailTo], msg.as_string())
        s.quit()
    except smtplib.SMTPException, e:
        print 'Error while sending mail'
        return False
    return True
# end send_mail

if __name__ == "__main__":
    #send_mail('sanity_params.ini','report/junit-noframes.html') 
    send_mail(sys.argv[1], sys.argv[2], sys.argv[3])
