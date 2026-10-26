/**
 * Builds the student survey in Google Forms, with a linked response sheet.
 *
 * How to run it:
 *   1. Open https://script.google.com and click "New project".
 *   2. Delete the sample code, paste this whole file, and click Save.
 *   3. Pick "createSurvey" in the function menu at the top and click Run.
 *   4. Approve the permissions. Google warns that the app is unverified
 *      because it is your own script: click Advanced, then "Go to project".
 *   5. Open the Execution log. The link to share and the link to edit are
 *      printed there. The form is also in your Google Drive.
 *
 * Running it twice creates two forms. Delete the extra one in Drive.
 *
 * Question order is deliberate. Everything about what students actually
 * experience comes first, and the only question about a registration system
 * comes last. Asking about the solution first primes people to report a
 * problem, and a reviewer checking whether the evidence is real will look for
 * exactly that.
 */

const SETTINGS = {
  title: 'Laptops at the Campus Gate: Student Survey',
  // Shown to students who have a question about the survey. Leave empty to hide.
  contactEmail: '',
  linkResponseSheet: true,
  // Requires a Google sign-in and allows one response per account. Useful if
  // your university uses Google accounts; it stops repeat submissions but some
  // students will not bother signing in. Emails are still not recorded.
  oneResponsePerPerson: false,
};

function createSurvey() {
  const form = FormApp.create(SETTINGS.title)
    .setDescription(introduction())
    .setProgressBar(true)
    .setAllowResponseEdits(false)
    .setShowLinkToRespondAgain(false)
    .setConfirmationMessage(
      'Thank you. Your answers have been recorded anonymously.'
    );

  if (SETTINGS.oneResponsePerPerson) form.setLimitOneResponsePerUser(true);

  // Page 1: consent
  const consent = form
    .addMultipleChoiceItem()
    .setTitle('Do you agree to take part?')
    .setHelpText(
      'Taking part is voluntary and you can stop at any time. Nothing you submit can be traced to you.'
    )
    .setRequired(true);
  consent.setChoices([
    consent.createChoice('Yes, I agree to take part', FormApp.PageNavigationType.CONTINUE),
    consent.createChoice('No', FormApp.PageNavigationType.SUBMIT),
  ]);

  // Page 2: about you
  page(form, 'About you', 'No names and no student numbers.');
  choice(form, 'What year of study are you in?', [
    'Year 1',
    'Year 2',
    'Year 3',
    'Year 4 or above',
    'Postgraduate',
  ], { other: true });
  choice(form, 'Where do you live during term?', [
    'On campus',
    'Off campus',
    'A mix of both',
  ]);
  checkboxes(form, 'Which of these do you regularly bring onto campus?', [
    'Laptop',
    'Tablet',
    'External hard drive',
    'Other electronic equipment',
    'None of these',
  ]);
  choice(form, 'In a typical week, how many days do you carry a laptop through a campus gate?', [
    'Never',
    '1 to 2 days',
    '3 to 4 days',
    '5 days or more',
  ]);

  // Page 3: at the gate
  page(form, 'At the gate', 'Think about what usually happens, not what is supposed to happen.');
  choice(form, 'When you pass through a campus gate carrying a laptop, how often is it checked?', [
    'Never',
    'Rarely',
    'Sometimes',
    'Usually',
    'Every time',
    'I do not carry a laptop through the gate',
  ]);
  checkboxes(form, 'When your laptop is checked, what usually happens?', [
    'The guard does not check it',
    'I show my student ID',
    'A serial number is written in a book or register',
    'I sign a book or register',
    'The guard looks at the laptop',
    'I show a receipt or another document',
    'I am not sure',
  ], { other: true, help: 'Tick everything that applies.' });
  choice(form, 'How long does a laptop check usually take, from joining the queue to walking through?', [
    'Under 30 seconds',
    '30 seconds to 1 minute',
    '1 to 3 minutes',
    '3 to 10 minutes',
    'More than 10 minutes',
    'I am not checked',
  ]);
  choice(form, 'Have you ever been stopped or delayed because a guard could not confirm the laptop was yours?', [
    'No',
    'Yes, once',
    'Yes, more than once',
    'Not sure',
  ]);
  choice(form, 'Has a gate check ever made you late for a class, exam or appointment?', [
    'Never',
    'Once',
    'Several times',
  ]);
  scale(
    form,
    'If someone tried to walk out of a campus gate with your laptop, how likely is it that the current checks would stop them?',
    'Very unlikely',
    'Very likely'
  );

  // Page 4: loss and theft. The last question branches.
  page(form, 'Lost and stolen devices');
  choice(form, 'Do you personally know another student whose laptop or device was lost or stolen on campus in the last 12 months?', [
    'No',
    'Yes, one person',
    'Yes, two or more people',
  ]);
  const ownLoss = form
    .addMultipleChoiceItem()
    .setTitle('Has a laptop or other device of yours ever been lost or stolen on campus?')
    .setRequired(true);

  // Page 5: only for students who answered yes above
  const incidentPage = page(
    form,
    'What happened',
    'Only share what you are comfortable sharing. Every question on this page is optional.'
  );
  choice(form, 'When did it happen?', [
    'In the last 6 months',
    '6 to 12 months ago',
    '1 to 2 years ago',
    'More than 2 years ago',
  ], { required: false, help: 'If it happened more than once, answer about the most recent time.' });
  checkboxes(form, 'What was it?', ['Laptop', 'Tablet', 'Phone'], { other: true, required: false });
  checkboxes(form, 'Who did you report it to?', [
    'Campus security',
    'The police',
    'A university office',
    'A lecturer or staff member',
    'I did not report it',
  ], { other: true, required: false });
  choice(form, 'Was it recovered?', ['Yes', 'No', 'Still waiting'], { required: false });
  choice(form, 'At the time, could you have proved the device was yours?', [
    'Yes, I had the serial number or a receipt',
    'Partly, I could describe it',
    'No',
  ], { required: false });
  checkboxes(form, 'What did losing it cost you?', [
    'The cost of a replacement',
    'Lost coursework or files',
    'A missed deadline or exam',
    'Having to borrow or share a device',
    'Time spent reporting and following up',
    'Nothing significant',
  ], { other: true, required: false });
  paragraph(form, 'If you did not report it, why not?');

  // Page 6: proving ownership, for everyone
  const ownershipPage = page(form, 'Proving a laptop is yours');
  choice(form, "Do you know your laptop's serial number?", [
    'Yes, I have it written down',
    'I know where to find it',
    'No',
    'I do not own a laptop',
  ]);
  choice(form, 'Do you still have proof of purchase for your laptop?', [
    'Yes, a receipt or invoice',
    'No, I lost it or never had one',
    'It was a gift',
    'I bought it second-hand',
    'I do not own a laptop',
  ]);
  paragraph(form, 'If your laptop were stolen tomorrow, how would you prove it is yours?');

  // Page 7: views. Kept last on purpose; see the note at the top.
  page(form, 'Your views');
  scale(
    form,
    'How much do you agree with this statement: "The way laptops are checked at campus gates needs to change."',
    'Strongly disagree',
    'Strongly agree'
  );
  scale(
    form,
    'If you could register your laptop once and have it recognised at the gate after that, how likely would you be to register it?',
    'Very unlikely',
    'Very likely'
  );
  checkboxes(form, 'What would worry you about registering your laptop with the university?', [
    'Who can see my personal details',
    'How my data is stored',
    'How long registration would take',
    'Being wrongly stopped at the gate',
    'Nothing would worry me',
  ], { other: true, required: false });
  paragraph(form, 'Is there anything else you want to tell us about laptops, the gates or campus security?');

  // Branching needs the pages to exist before the choices can point at them.
  ownLoss.setChoices([
    ownLoss.createChoice('Yes, it was stolen', incidentPage),
    ownLoss.createChoice('Yes, it was lost', incidentPage),
    ownLoss.createChoice('Yes, but I do not know whether it was lost or stolen', incidentPage),
    ownLoss.createChoice('No', ownershipPage),
  ]);

  if (SETTINGS.linkResponseSheet) {
    const sheet = SpreadsheetApp.create(SETTINGS.title + ' (responses)');
    form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());
    Logger.log('Responses sheet:     ' + sheet.getUrl());
  }

  const shareUrl = form.getPublishedUrl();
  let shortUrl = shareUrl;
  try {
    shortUrl = form.shortenFormUrl(shareUrl);
  } catch (error) {
    // Some accounts cannot shorten links. The long one works just as well.
  }
  Logger.log('Share with students: ' + shortUrl);
  Logger.log('Edit the form:       ' + form.getEditUrl());
}

function introduction() {
  const lines = [
    'We are studying how laptops and other devices are checked at campus gates, and how often they are lost or stolen. Your answers will help us understand what students actually experience.',
    'It takes about 5 minutes. It is anonymous: we do not collect your name, email address or student number. Questions about lost or stolen devices are optional.',
  ];
  if (SETTINGS.contactEmail) {
    lines.push('Questions about this survey: ' + SETTINGS.contactEmail);
  }
  return lines.join('\n\n');
}

function page(form, title, help) {
  const item = form.addPageBreakItem().setTitle(title);
  if (help) item.setHelpText(help);
  return item;
}

function choice(form, title, options, opts = {}) {
  const item = form
    .addMultipleChoiceItem()
    .setTitle(title)
    .setChoiceValues(options)
    .setRequired(opts.required ?? true);
  if (opts.help) item.setHelpText(opts.help);
  if (opts.other) item.showOtherOption(true);
  return item;
}

function checkboxes(form, title, options, opts = {}) {
  const item = form
    .addCheckboxItem()
    .setTitle(title)
    .setChoiceValues(options)
    .setRequired(opts.required ?? true);
  if (opts.help) item.setHelpText(opts.help);
  if (opts.other) item.showOtherOption(true);
  return item;
}

function scale(form, title, lowLabel, highLabel) {
  return form
    .addScaleItem()
    .setTitle(title)
    .setBounds(1, 5)
    .setLabels(lowLabel, highLabel)
    .setRequired(true);
}

function paragraph(form, title) {
  return form.addParagraphTextItem().setTitle(title).setRequired(false);
}
