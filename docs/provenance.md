# Project history

## Academic project, 2023–2024

The Advanced Smart Saline Assistance System was built as a final-year B.E. Electronics & Telecommunication team project at VCET (University of Mumbai) by Chandan Thakur, Mayank Patil, Manthan Patil and Omkar Joshi. Mayank Patil was the project architect and backend developer.

The team built the physical prototype (drip sensors, heart-rate and body-temperature sensing, 3D-printed drip-chamber housing, tube-squeezing mechanism, bedside controller and radio link) and the Flask dashboard. They wrote a technical paper and presented the project at five competitions. The paper, photos, 3D part models and certificates in `docs/` are from that work.

## This repository, November 2026

The code was gathered from the original project files and tidied up for publication. The main changes from the 2024 code:

- **Radio code:** the radio is set up only when first used. Each bedside node's latest reading is tracked separately and marked stale after 5 seconds. All five values in a packet are decoded correctly (the old code kept only the low byte of each).
- **Command sender:** the original sender script survived only as compiled Python, so it was rebuilt from that as `sender.py`. It keeps the same radio addresses, three-byte commands and two-second repeat.
- **Security:** passwords are hashed, forms are protected against cross-site requests, the security code is checked on the server, and database credentials come from environment variables.
- **Bug fixes:** phone numbers stored as text, one active therapy per patient and channel, Finish no longer depends on the radio, clear error messages for bad input, and the time remaining is now estimated instead of fixed.
- **Vital signs:** the original Arduino code for heart rate and temperature wasn't among the recovered files. The bedside sketch was rewritten for the team's sensors (MAX30102 and MLX90614), and the radio packet, dashboard and tests were extended to carry heart rate and body temperature.
- **Cleanup:** removed unused template files and images, loaded each front-end library once, and added automated tests and these docs.
- **Media:** the diagrams were redrawn from the team's presentation and paper, the 3D part animations come from the team's CAD models, and the narrated explainer video was made for this repository (computer-generated voice). Its dashboard scenes are real screens of this code running with sample data.

No patient records or credentials are included in the repository.

## Project materials

| Material | Location |
| --- | --- |
| Technical paper | [research/technical-paper.docx](research/technical-paper.docx) |
| Prototype photos | [images/prototype-lab.jpg](images/prototype-lab.jpg), [images/lab-setup.jpg](images/lab-setup.jpg) |
| Animated explainer and 3D part videos | [videos/](videos/) |
| Competition certificates | [evidence/achievements.pdf](evidence/achievements.pdf) |

[Back to README](../README.md)
