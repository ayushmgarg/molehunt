---
title: Zephyr Labs Q3 Product Roadmap
auto_slots:
  zw: 70
  nbsp: 24
  hom: 22
---
# Zephyr Labs: Q3 Product Roadmap (Confidential)

This roadmap sets out what the product group will {{lex:deliver|ship}} between {{dat:1 July|July 1}} and {{dat:30 September|September 30}}. It is a working document for the twelve people on the distribution list{{pun:,|}} and it should not {{lex:leave|exit}} the shared drive. Questions go to the programme office{{spc:.  |. }}Do not forward this file.

## 1. Goals for the quarter

Our main goal is to {{lex:finish|complete}} the Harbor sync engine and to {{spl:prioritize|prioritise}} reliability over new features. Customer surveys show that slow sync is the {{lex:biggest|largest}} reason for churn, so the team will {{spl:optimize|optimise}} the upload path first. A second goal is to {{spl:standardize|standardise}} the release checklist so that every squad can {{lex:check|verify}} a build the same way. The third goal is to {{lex:cut|reduce}} support tickets by {{num:1,200|1 200}} per month{{spc:.  |. }}We will {{lex:measure|track}} this weekly.

## 2. Harbor sync engine

The sync engine will {{lex:move|shift}} from polling to a push model in {{dat:14 July|July 14}}{{pun:'|’}}s sprint. Engineering will {{spl:analyze|analyse}} the current queue and {{lex:remove|drop}} the legacy retry loop. Early tests on a {{lex:small|modest}} cohort of {{num:2,500|2 500}} accounts cut median latency from {{num:4.8|4,8}} seconds to under two seconds{{spc:.  |. }}The team will {{lex:publish|release}} a beta on {{dat:28 July|July 28}}.

Risks are {{lex:clear|plain}}: the push model needs a new gateway{{pun:,|}} a change to billing hooks{{pun:,|}} and extra on-call {{spl:labor|labour}}. The squad will {{spl:minimize|minimise}} risk by keeping the old path behind a flag until {{dat:25 August|August 25}}. If error rates {{lex:rise|climb}} above {{num:0.5|0,5}} percent, the flag will {{lex:return|revert}} traffic to polling within ten minutes.

## 3. Mobile app

The mobile squad will {{spl:finalize|finalise}} the new {{spl:color|colour}} palette and {{lex:fix|repair}} the dark-mode contrast bugs. Design has {{spl:organized|organised}} a review on {{dat:9 August|August 9}}{{spc:.  |. }}The squad will also {{lex:begin|start}} offline drafts{{pun:,|}} which our {{spl:favorite|favourite}} customers {{lex:requested|asked for}} last year. Offline drafts {{lex:need|require}} a local {{spl:catalog|catalogue}} of templates{{pun:,|}} capped at {{num:5,000|5 000}} items per device.

We will not {{spl:authorize|authorise}} a public launch until crash rates fall below one per {{num:10,000|10 000}} sessions. Battery {{spl:behavior|behaviour}} on older phones remains a {{lex:concern|worry}}, and the squad will {{lex:test|trial}} on six reference devices.

## 4. Admin console

The admin console gets three changes. First, admins will {{lex:get|receive}} an audit view that shows who opened a shared file. Second, the {{spl:license|licence}} page will {{lex:show|display}} seat use per team. Third, the team will {{spl:centralize|centralise}} role settings so that a manager can {{lex:give|grant}} access in one step{{spc:.  |. }}The console work is {{lex:planned|scheduled}} for {{dat:4 September|September 4}}.

## 5. Data and {{spl:modeling|modelling}}

Analytics will {{lex:build|create}} a churn model using {{num:18,000|18 000}} anonymised account histories. The model is a plain logistic score{{pun:,|}} and the team will {{spl:summarize|summarise}} its inputs in a one-page note. Data {{spl:defense|defence}} rules apply: no raw records {{lex:leave|exit}} the warehouse, and every export needs a ticket{{spc:.  |. }}The analysts will {{spl:recognize|recognise}} each export in the weekly review.

## 6. Budget and staffing

The quarter has a budget of {{num:1,450,000|1 450 000}} dollars. Contractors {{lex:account for|make up}} {{num:22.5|22,5}} percent of spend{{pun:,|}} and the finance lead will {{lex:check|verify}} invoices every month. Travel is {{spl:canceled|cancelled}} unless a customer visit is {{lex:essential|vital}}{{spc:.  |. }}Any {{spl:traveling|travelling}} staff must log trips in the {{spl:gray|grey}} expense sheet.

Hiring is {{lex:limited|restricted}} to two roles: a site reliability engineer and a mobile tester. Interviews {{lex:begin|start}} on {{dat:21 July|July 21}}{{pun:,|}} and offers should go out by {{dat:15 August|August 15}}.

## 7. Milestones

- Harbor beta: {{dat:28 July|July 28}}{{pun: -| –}} owner, sync squad.
- Palette review: {{dat:9 August|August 9}}{{pun: -| –}} owner, mobile squad.
- Flag removal: {{dat:25 August|August 25}}{{pun: -| –}} owner, platform squad.
- Console release: {{dat:4 September|September 4}}{{pun: -| –}} owner, admin squad.
- Quarter review: {{dat:30 September|September 30}}{{pun: -| –}} owner, programme office.

## 8. Dependencies and open questions

The sync work {{lex:depends on|relies on}} the gateway team, who {{lex:hope|expect}} to {{lex:finish|complete}} their load tests by {{dat:11 August|August 11}}. If they {{lex:slip|fall behind}}, the beta will {{lex:wait|pause}} rather than {{lex:skip|bypass}} the tests. Security will {{spl:analyze|analyse}} the new tokens and {{lex:help|assist}} the squad to {{lex:choose|select}} a key rotation period. Legal must {{spl:authorize|authorise}} the updated terms before we {{lex:alter|amend}} the {{spl:license|licence}} page.

Several questions are still {{lex:open|unresolved}}. Should the console {{lex:keep|retain}} audit entries for {{num:365|three hundred sixty-five}} days or {{num:730|seven hundred thirty}}? Can the mobile squad {{lex:buy|purchase}} more test devices at {{num:1,100|1 100}} dollars each? Who will {{spl:organize|organise}} the {{spl:center|centre}} of excellence for reliability{{pun:,|}} and when will it {{lex:meet|convene}}? The programme office will {{lex:gather|collect}} answers and {{spl:summarize|summarise}} them on {{dat:18 August|August 18}}. Teams should {{lex:send|dispatch}} notes early, {{lex:try|aim}} to keep them short, and {{lex:avoid|skip}} attachments. We {{lex:want|wish}} each squad to {{spl:recognize|recognise}} the trade-offs and to {{lex:state|declare}} them {{lex:plainly|clearly}}. Teams that {{spl:fulfill|fulfil}} their goals early may {{lex:ask|request}} extra scope{{pun:,|}} subject to a {{lex:quick|rapid}} review. Any {{lex:urgent|pressing}} change will be {{spl:labeled|labelled}} in the tracker and {{spl:catalogued|cataloged}} by {{dat:1 September|September 1}}.

## 9. Handling rules

This document is {{lex:numbered|tagged}} per reader. Do not paste it into chat tools{{pun:,|}} do not {{lex:print|output}} it at home{{pun:,|}} and do not {{lex:share|pass on}} screenshots. If you {{spl:realize|realise}} a copy has gone astray, {{lex:tell|inform}} the programme office at once. We {{spl:emphasize|emphasise}} that the roadmap may {{lex:change|shift}} and that dates are targets, not promises{{pun:...|…}}

Thank you for keeping this {{lex:private|confidential}}.
