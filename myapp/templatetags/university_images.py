from django import template
from django.templatetags.static import static

register = template.Library()

university_image_urls = {
    "BOSTON COLLEGE": "bostoncollege.png",
    "BOSTON UNIVERSITY": "bostonu.png",
    "BROWN UNIVERSITY": "brown.jpg",
    "CALIFORNIA INSTITUTE OF TECHNOLOGY": "caltech.png",
    "UNIVERSITY OF CHICAGO": "chicago.png",
    "CARNIEGE MELLON UNIVERSITY": "cmu.png",
    "COLUMBIA UNIVERSITY IN THE CITY OF NEW YORK": "columbia.png",
    "CORNELL UNIVERSITY": "cornell.png",
    "DARTMOUTH COLLEGE": "dartmouth.png",
    "DUKE UNIVERSITY": "duke.png",
    "EMORY UNIVERSITY": "emory.jpg",
    "FLORIDA STATE UNIVERSITY": "floridastate.jpeg",
    "GEORGETOWN UNIVERSITY": "georgetown.png",
    "UNIVERSITY OF GEORGIA": "georgia.png",
    "GEORGIA INSTITUTE OF TECHNOLOGY-MAIN CAMPUS": "georgiatech.png",
    "HARVARD UNIVERSITY": "harvard.jpg",
    "JOHNS HOPKINS UNIVERSITY": "johnshopkins.png",
    "LEHIGH UNIVERSITY": "lehigh.png",
    "UNIVERSITY OF MARYLAND-COLLEGE PARK": "maryland.png",
    "UNIVERSITY OF MICHIGAN-ANN ARBOR": "michiganannarbor.png",
    "MASSACHUSETTS INSTITUTE OF TECHNOLOGY": "mit.png",
    "NORTH CAROLINA STATE UNIVERSITY AT RALEIGH": "northcarolina.png",
    "NORTHEASTERN UNIVERSITY": "northeastern.png",
    "NORTHWESTERN UNIVERSITY": "northwestern.png",
    "UNIVERSITY OF NOTRE DAME": "notredame.png",
    "NEW YORK UNIVERSITY": "nyu.png",
    "OHIO STATE UNIVERSITY-MAIN CAMPUS": "ohiostate.jpg",
    "PRINCETON UNIVERSITY": "princeton.png",
    "PURDUE UNIVERSITY-MAIN CAMPUS": "purdue.png",
    "RICE UNIVERSITY": "rice.png",
    "UNIVERSITY OF ROCHESTER": "rochester.png",
    "RUTGERS UNIVERSITY-NEW BRUNSWICK": "rutgers.png",
    "STANFORD UNIVERSITY": "stanford.png",
    "TEXAS A&M UNIVERSITY-CENTRAL TEXAS": "texasam.png",
    "TUFTS UNIVERSITY": "tufts.png",
    "UNIVERSITY OF CALIFORNIA-SANTA BARBARA": "ucsantabarbara.png",
    "UNIVERSITY OF CALIFORNIA-SAN DIEGO": "ucsandiego.png",
    "UNIVERSITY OF CALIFORNIA-DAVIS": "ucdavis.png",
    "UNIVERSITY OF CALIFORNIA-LOS ANGELES": "ucla.png",
    "UNIVERSITY OF CALIFORNIA-IRVINE": "ucirvine.png",
    "UNIVERSITY OF CALIFORNIA-BERKELEY": "ucberkeley.png",
    "UNIVERSITY OF ILLINOIS URBANA-CHAMPAIGN": "uiuc.jpg",
    "UNIVERSITY OF PENNSYLVANIA": "upenn.png",
    "THE UNIVERSITY OF TEXAS AT AUSTIN": "utaustin.png",
    "UNIVERSITY OF VIRGINIA-MAIN CAMPUS": "virginia.png",
    "WAKE FOREST UNIVERSITY": "wakeforest.png",
    "UNIVERSITY OF WASHINGTON-SEATTLE CAMPUS": "washington.png",
    "WASHINGTON UNIVERSITY IN ST LOUIS": "washu.png",
    "UNIVERSITY OF WISCONSIN-MADISON": "wisconsinmadison.png",
    "YALE UNIVERSITY": "yale.png"
    # Add more universities here
}

@register.simple_tag
def university_image_url(university_name):
    url = university_image_urls.get(university_name.upper())
    if url:
        return static(f"university_images/{url}")
    return university_image_urls.get(university_name, static("university_icon2.png"))
