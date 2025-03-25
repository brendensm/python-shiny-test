from datetime import date
import json
import pandas as pd
import requests
from shiny import App, ui, render, reactive, req
import asyncio
import uuid  


# Function to check if we're running in a browser/Shinylive environment
def is_pyodide_environment():
    try:
        import pyodide
        return True
    except ImportError:
        return False

# Initialize empty DataFrame for submissions
submissions_df = pd.DataFrame(
    columns=["RowID", "Timestamp", "BeverageType", "BeverageName", "Recommendation", "Reason"]
)

# Helper function to convert first letter to uppercase
def str_to_sentence(text):
    if not text:
        return ""
    return text[0].upper() + text[1:].lower()

# CSS styles
css = """
    /* Base styling */
    img.recommendation {
        max-height: 150px; 
        width: auto; 
        object-fit: contain;
        margin: 0 auto;
    }
    .green-result {color: green; font-weight: 700;}
    .yellow-result {color: orange; font-weight: 700;}
    .red-result {color: red; font-weight: 700;}
    .recommendation-text {font-weight: bold; margin-top: 10px; text-align: center;}
    
    /* Table styling */
    th {
        text-align: left !important;
        font-weight: bold !important;
    }
    
      /* Delete button styling */
    .delete-row {
        cursor: pointer;
    }
    
    .delete-row:hover {
        opacity: 0.8;
    }
    
    /* Button container */
    .button-container {
        display: flex;
        gap: 8px;
        margin-bottom: 15px;
    }
    
    /* Nav styling */
    .nav-pills {
        margin-bottom: 20px;
    }
    
    .nav-link {
        color: #005EA2;
        margin-left: 5px;
    }
    
    .nav-pills .nav-link.active {
        background-color: #005EA2;
    }
    
    /* Guidelines images */
    .guidelines-img {
        width: 100%;
        height: auto;
        cursor: pointer;
    }
    
    /* Lightbox styling */
    .lightbox-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.9);
        z-index: 1000;
        justify-content: center;
        align-items: center;
    }
    
    .lightbox-content {
        max-width: 90%;
        max-height: 90%;
    }
    
    .lightbox-close {
        position: absolute;
        top: 15px;
        right: 15px;
        color: white;
        font-size: 30px;
        cursor: pointer;
    }
    
    .clickable-image {
        cursor: pointer;
    }
    
    /* Mobile optimizations */
    @media screen and (max-width: 768px) {
        img.recommendation {
            max-height: 80px;
            max-width: 100%;
        }
        .recommendation-container {
            height: auto !important;
            max-height: none !important;
            overflow: visible !important;
        }
        .table-wrapper {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        #full_guidelines img, #snack_guidelines img {
            width: 100%;
        }
    }
    
    /* Add some spacing for mobile */
    @media screen and (max-width: 576px) {
        .col-12.d-flex {
            flex-direction: column;
            align-items: center;
        }
        
        .nav-pills {
            margin-top: 10px;
        }
    }
"""

# Main app UI
app_ui = ui.page_fluid(
  
   
    # Head section with meta tags, CSS, and JS
    ui.tags.head(
        ui.tags.title("SSC Calculator"),
        ui.tags.meta(name="viewport", content="width=device-width, initial-scale=1"),
        ui.tags.style(css),
        ui.tags.link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"),
        ui.tags.script(src="https://code.jquery.com/jquery-3.6.0.min.js"),
        ui.tags.script("""
$(document).ready(function() {
  // Click handler for the guidelines image
  $(document).on('click', '#full_guidelines img, #snack_guidelines img, .clickable-image', function() {
    var imgSrc = $(this).attr('src');
    if (!imgSrc) {
      imgSrc = $(this).find('img').attr('src');
    }
    
    if (imgSrc) {
      $('#lightbox-img').attr('src', imgSrc);
      $('#lightbox').css('display', 'flex');
    }
  });
  
  // Close lightbox when clicking on the X or anywhere outside the image
  $(document).on('click', '.lightbox-close, .lightbox-overlay', function(e) {
    if (e.target === this) {
      $('#lightbox').css('display', 'none');
    }
  });
  
  // Prevent clicks on the image itself from closing the lightbox
  $(document).on('click', '.lightbox-content', function(e) {
    e.stopPropagation();
  });
  
  // Handle tab navigation
  $(document).on('click', '.nav-link', function() {
    let target = $(this).data('value');
    $('.tab-content').hide();
    $('#' + target).show();
    $('.nav-link').removeClass('active');
    $(this).addClass('active');
  });
  
  // Initialize first tab as active
  $('.nav-link:first').addClass('active');
  $('.tab-content:first').show();
});
        """)
    ),
    
    # Navigation bar with pills
    ui.tags.div(
        {"class": "container-fluid"},
        ui.tags.div(
            {"class": "row"},
            ui.tags.div(
                {"class": "col-12 d-flex justify-content-between align-items-center"},
                # Logo on left
                ui.tags.div(
                    ui.tags.img(src="https://raw.githubusercontent.com/brendensm/calc-test/main/www/logo_transparent_background.png", height="50px", style="margin-right:10px;")
                ),
                # Navigation tabs on right
                ui.tags.ul(
                    {"class": "nav nav-pills"},
                    ui.tags.li(
                        {"class": "nav-item"},
                        ui.tags.a("Beverages", {"class": "nav-link", "data-value": "beverages"})
                    ),
                    ui.tags.li(
                        {"class": "nav-item"},
                        ui.tags.a("Snacks", {"class": "nav-link", "data-value": "snacks"})
                    ),
                    ui.tags.li(
                        {"class": "nav-item"},
                        ui.tags.a("About", {"class": "nav-link", "data-value": "about"})
                    )
                )
            )
        )
    ),
    
    # Hidden element for triggering UI updates
    ui.tags.div({"id": "hidden_trigger", "style": "display: none;"}),
    
    # Content sections for each tab
    # 1. Beverages Tab
    ui.tags.div(
        {"id": "beverages", "class": "tab-content container-fluid"},
        ui.tags.div(
            {"class": "row mt-3"},
            ui.tags.div(
                {"class": "col-12"},
                ui.tags.h2("Beverage Nutrition Calculator")
            )
        ),
        ui.tags.div(
            {"class": "row"},
            # Column for input form
            ui.tags.div(
                {"class": "col-12 col-md-4 mb-3"},
                ui.tags.div(
                    {"class": "card"},
                    ui.tags.div(
                        {"class": "card-header"},
                        "Input Information"
                    ),
                    ui.tags.div(
                        {"class": "card-body"},
                        ui.p(
                            "K-12 facilities should first use the ",
                            ui.tags.a("USDA Smart Snacks in School Product Calculator",
                                      href="https://foodplanner.healthiergeneration.org/calculator/"),
                            " to determine if a beverage is compliant with the USDA guidelines. ",
                            "The SSC Beverage Calculator can then be used to determine if a USDA-compliant beverage is in ",
                            "the green or yellow category."
                        ),
                        ui.input_select(
                            "beverage_type",
                            "Select Beverage Type:",
                            choices=["Juice", "Milk", "Other"]
                        ),
                        ui.input_text(
                            "beverage_name",
                            "Beverage Name:",
                            placeholder="Optional"
                        ),
                        ui.input_radio_buttons(
                            "artificial",
                            ui.HTML("Does this contain artificial sweeteners?<sup>1</sup>"),
                            choices={"True": "Yes", "False": "No"},
                            inline=True
                        ),
                        ui.output_ui("dynamic_inputs"),
                        ui.tags.h6(
                            ui.HTML("<sup>1</sup>Artificial sweeteners include acesulfame potassium, advantame, aspartame, neotame, saccharin, and sucralose. Stevia and monk fruit are not considered to be artificial sweeteners."),
                            style="font-size:.8em; font-weight:normal;"
                        ),
                        ui.hr(),
                        ui.tags.div(
                            {"class": "button-container"},
                            ui.input_action_button("submit", "Submit", class_="btn-primary"),
                            ui.input_action_button(
                                "save_data", "Save data", 
                                class_="btn-success", 
                                icon=ui.tags.i({"class": "fas fa-download"})
                            ),
                            
                
                        )

                    )
                )
            ),
            
            # Column for results
            ui.tags.div(
                {"class": "col-12 col-md-8"},
                
                # Recommendation card
                ui.tags.div(
                    {"class": "card mb-3"},
                    ui.tags.div(
                        {"class": "card-header"},
                        "Recommendation"
                    ),
                    ui.tags.div(
                        {"class": "card-body recommendation-container", "style": "max-height: 250px; overflow: hidden;"},
                        ui.output_ui("recommendation_image"),
                        ui.output_ui("recommendation_text")
                    )
                ),
                
                # Table card
                ui.tags.div(
                    {"class": "card"},
                    ui.tags.div(
                        {"class": "card-header"},
                        "Submissions"
                    ),
                    ui.tags.div(
                        {"class": "card-body table-wrapper"},
                        ui.output_ui("submissions_table")
                    )
                )
            )
        )
    ),
    
    # 2. Snacks Tab
    ui.tags.div(
        {"id": "snacks", "class": "tab-content container-fluid", "style": "display: none;"},
        ui.tags.div(
            {"class": "row mt-3"},
            ui.tags.div(
                {"class": "col-12"},
                ui.tags.h2("Snack Guidelines")
            )
        ),
        ui.tags.div(
            {"class": "row"},
            ui.tags.div(
                {"class": "col-md-7 col-12"},
                ui.tags.div(
                    {"class": "card"},
                    ui.tags.div(
                        {"class": "card-header"},
                        "Snack Guidelines"
                    ),
                    ui.tags.div(
                        {"class": "card-body"},
                        ui.p(
                            "To determine if it is a green, yellow, or red category item use the ",
                            ui.tags.a(
                                "USDA Smart Snacks in School Product Calculator.",
                                href="https://foodplanner.healthiergeneration.org/calculator/"
                            )
                        )
                    )
                )
            ),
            ui.tags.div(
                {"class": "col-md-5 col-12"},
                ui.tags.div(
                    {"class": "card"},
                    ui.tags.div(
                        {"class": "card-body"},
                        ui.tags.div(
                            {"id": "snack_guidelines", "class": "clickable-image"},
                            ui.tags.img(
                                src="https://raw.githubusercontent.com/brendensm/calc-test/main/www/snack_guidelines.png",
                                width="100%",
                                class_="guidelines-img"
                            )
                        )
                    )
                )
            )
        )
    ),
    
    # 3. About Tab
    ui.tags.div(
        {"id": "about", "class": "tab-content container-fluid", "style": "display: none;"},
        ui.tags.div(
            {"class": "row mt-3"},
            ui.tags.div(
                {"class": "col-12"},
                ui.tags.h2("About")
            )
        ),
        ui.tags.div(
            {"class": "row"},
            ui.tags.div(
                {"class": "col-md-7 col-12"},
                ui.tags.div(
                    {"class": "card"},
                    ui.tags.div(
                        {"class": "card-header"},
                        "About the Sugar Smart Coalition"
                    ),
                    ui.tags.div(
                        {"class": "card-body"},
                        ui.p(
                            "The Sugar Smart Coalition (SSC) is committed to advocacy, "
                            "education, equitable practice, and policy that improves "
                            "healthy food and beverage options and choices. "
                            "SSC's vision is to reduce added sugar consumption "
                            "and its negative health impacts on our Michigan communities."
                        ),
                        ui.p(
                            "SSC's beverage guidelines were developed by member dietitians in the "
                            "Nutrition Guidelines Committee based on standards set by the American Heart "
                            "Association, ChangeLab Solutions, Healthy Eating Research, and the National "
                            "Alliance for Nutrition and Activity. Using SSC's beverage guidelines, drinks "
                            "fall into one of three categories:"
                        ),
                        ui.tags.ul(
                            ui.tags.li(ui.tags.strong("Green / Go For It"), " - no added sugar, artificial sweeteners, or sugar alcohol."),
                            ui.tags.li(ui.tags.strong("Yellow / OK Sometimes"), " - minimal added sugar, zero-calorie or low-calorie sweeteners."),
                            ui.tags.li(ui.tags.strong("Red / Maybe Not"), " - added sugar and caloric sweeteners.")
                        ),
                        ui.p(
                            "To learn more about the Sugar Smart Coalition, or to share any feedback with us, visit our ",
                            ui.tags.a("Facebook page", href="https://www.facebook.com/SugarSmartCoalition", target="_blank"),
                            " or ",
                            ui.tags.a("email us.", href="mailto:sugarsmartcoalition@gmail.com", target="_blank")
                        )
                    )
                )
            ),
            ui.tags.div(
                {"class": "col-md-5 col-12"},
                ui.tags.div(
                    {"class": "card"},
                    ui.tags.div(
                        {"class": "card-header"},
                        "Full Guidelines"
                    ),
                    ui.tags.div(
                        {"class": "card-body"},
                        ui.tags.div(
                            {"id": "full_guidelines", "class": "clickable-image"},
                            ui.tags.img(
                                src="https://raw.githubusercontent.com/brendensm/calc-test/main/www/guidelines_full.png",
                                width="100%",
                                class_="guidelines-img"
                            )
                        )
                    )
                )
            )
        )
    ),
    
    # Lightbox overlay
    ui.tags.div(
        {"id": "lightbox", "class": "lightbox-overlay"},
        ui.tags.div({"class": "lightbox-close"}, "×"),
        ui.tags.img({"id": "lightbox-img", "class": "lightbox-content"})
    ),
    
    # Hidden element for JavaScript code
    ui.tags.div(id="custom_js", style="display:none;")
)

def server(input, output, session):
    # Store submissions in a reactive value
    submissions = reactive.Value(submissions_df)
    
    # Dynamic inputs based on beverage type
    @output
    @render.ui
    def dynamic_inputs():
        beverage_type = input.beverage_type()
        
        if beverage_type == "Juice":
            return ui.div(
                ui.input_numeric("juice_serving_size", "Serving Size (oz):", min=0, value=None),
                ui.input_radio_buttons(
                    "is_100_percent",
                    "Is this 100% Juice?",
                    choices={"True": "Yes", "False": "No"},
                    inline=True
                )
            )
        elif beverage_type == "Milk":
            return ui.div(
                ui.input_radio_buttons(
                    "is_flavored",
                    "Is the milk flavored?",
                    choices={"True": "Yes", "False": "No"},
                    inline=True
                ),
                ui.input_radio_buttons(
                    "is_sweetened",
                    "Is the milk sweetened?",
                    choices={"True": "Yes", "False": "No"},
                    inline=True
                )
            )
        elif beverage_type == "Other":
            return ui.div(
                ui.input_numeric("total_sugar", "Total Sugar (grams):", min=0, value=None),
                ui.input_numeric("added_sugar", "Added Sugar (grams):", min=0, value=None),
                ui.tags.div(
                    "Note: Added sugar must be less than or equal to total sugar",
                    style="font-size: 0.8em; color: #666; margin-top: 5px;"
                )
            )
        else:
            return ui.div()

    # Helper function to validate inputs
    def validate_inputs(beverage_type):
        if beverage_type == "Juice":
            juice_size = input.juice_serving_size()
            if juice_size is None or juice_size <= 0:
                ui.notification_show(
                    "Please enter a valid serving size greater than 0",
                    type="error"
                )
                return False
        elif beverage_type == "Other":
            total_sugar = input.total_sugar()
            added_sugar = input.added_sugar()
            
            if total_sugar is None or total_sugar < 0:
                ui.notification_show(
                    "Please enter a valid total sugar amount (0 or greater)",
                    type="error"
                )
                return False
                
            if added_sugar is None or added_sugar < 0:
                ui.notification_show(
                    "Please enter a valid added sugar amount (0 or greater)",
                    type="error"
                )
                return False
                
            if added_sugar > total_sugar:
                ui.notification_show(
                    "Added sugar cannot be greater than total sugar",
                    type="error"
                )
                return False
        
        return True

    # Function to generate reasons based on inputs and criteria
    def generate_reasons(criteria_list, reason_texts):
        return [reason for criteria, reason in zip(criteria_list, reason_texts) if criteria]

    # Store recommendation result in a reactive value
    recommendation_result = reactive.Value(None)
    
    row_to_delete = reactive.Value(None)
    
    # Helper function for debugging recommendations
    # def debug_recommendation_values():
    #     # Get input values
    #     beverage_type = input.beverage_type()
    #     
    #     if beverage_type == "Other":
    #         total_sugar = input.total_sugar()
    #         added_sugar = input.added_sugar()
    #         has_artificial = input.artificial() 
    #         
    #         # Log values and conditions
    #         print(f"Debug - Other beverage inputs:")
    #         print(f"  total_sugar: {total_sugar} (type: {type(total_sugar)})")
    #         print(f"  added_sugar: {added_sugar} (type: {type(added_sugar)})")
    #         print(f"  has_artificial: {has_artificial} (type: {type(has_artificial)})")
    #         
    #         # Check conditions
    #         condition1 = total_sugar <= 12
    #         condition2 = added_sugar == 0
    #         condition3 = not has_artificial
    #         
    #         print(f"  Condition checks:")
    #         print(f"    total_sugar <= 12: {condition1}")
    #         print(f"    added_sugar == 0: {condition2}")
    #         print(f"    not has_artificial: {condition3}")
    #         print(f"    All conditions met for GREEN: {condition1 and condition2 and condition3}")
    #         
    #         return {
    #             "total_sugar": total_sugar,
    #             "added_sugar": added_sugar,
    #             "has_artificial": has_artificial,
    #             "conditions_met": condition1 and condition2 and condition3
    #         }
    #     
    #     return None
    
    # Check environment on startup
    @reactive.Effect
    def check_environment():
        # Check if we're running in a browser environment
        pyodide_env = is_pyodide_environment()
        print(f"Running in Pyodide/browser environment: {pyodide_env}")
        
        # Test numeric comparisons
        test_val1 = 0
        test_val2 = 0.0
        print(f"Numeric comparison test: {test_val1} == {test_val2} is {test_val1 == test_val2}")
        
        # Test boolean operations
        test_bool = "True" == "True"
        print(f"Boolean test: 'True' == 'True' evaluates to {test_bool}")
        print(f"Boolean negation: not {test_bool} evaluates to {not test_bool}")
    
    # Validate beverage input and calculate recommendation
    @reactive.Effect
    @reactive.event(input.submit)
    def validate_and_store_beverage():
        # Require beverage type
        req(input.beverage_type())
        
        beverage_type = input.beverage_type()
        
        # Add debug logging
        #debug_values = debug_recommendation_values()
        #print(f"Debug values: {debug_values}")
        
        print(f"bev_type: {beverage_type}")
        
        # Validate inputs based on beverage type
        if not validate_inputs(beverage_type):
            return
        
        # Initialize variables
        recommendation_text = ""
        recommendation_color = ""
        reason = None
        text_label = ""
        
        if beverage_type == "Milk":
            # Require all milk inputs
            req(input.is_flavored(), input.is_sweetened(), input.artificial())
            
            is_flavored = input.is_flavored() == "True"
            is_sweetened = input.is_sweetened() == "True"
            has_artificial = input.artificial() == "True"
            
            criteria = [is_sweetened, is_flavored, has_artificial]
            reasons_text = ["milk sweetened", "milk flavored", "contains artificial sweeteners"]
            
            if not any(criteria):
                recommendation_text = "goforit.png"
                recommendation_color = "green"
                text_label = "Go For It!"
            else:
                recommendation_text = "maybenot.png"
                recommendation_color = "red"
                text_label = "Maybe Not"
                
                reasons = generate_reasons(criteria, reasons_text)
                if reasons:
                    reason = str_to_sentence(", ".join(reasons))
        
        elif beverage_type == "Juice":
            # Require juice inputs
            req(input.juice_serving_size(), input.is_100_percent())
            
            juice_size = input.juice_serving_size()
            juice_size_ok = juice_size <= 12
            is_100_percent = input.is_100_percent() == "True"
            
            criteria = [not juice_size_ok, not is_100_percent]
            reasons_text = ["serving size > 12oz", "not 100% juice"]
            
            if is_100_percent and juice_size_ok:
                recommendation_text = "oksometimes.png"
                recommendation_color = "yellow"
                text_label = "OK Sometimes"
            else:
                recommendation_text = "maybenot.png"
                recommendation_color = "red"
                text_label = "Maybe Not"
                
                reasons = generate_reasons(criteria, reasons_text)
                if reasons:
                    reason = str_to_sentence(", ".join(reasons))
        
        elif beverage_type == "Other":
            # Require other beverage inputs
            req(input.total_sugar())
            
            # Convert input values to floats
            try:
                total_sugar = float(input.total_sugar())
                added_sugar = float(input.added_sugar())
            except ValueError:
                ui.notification_show(
                    "Please enter valid numeric values for total and added sugar.",
                    type="error"
                )
                return
    
            has_artificial = input.artificial() == "True"
    
            # Debug output
            print(f"Other beverage values: total={total_sugar}, added={added_sugar}, artificial={has_artificial}")
            
            # Check individual conditions and collect reasons
            reasons = []
            
            # Check conditions for green (negated to find failures)
            if total_sugar > 12.0:
                reasons.append("Total sugar exceeds 12g")
            
            if added_sugar > 0.0:
                reasons.append("Contains added sugar")
            
            if has_artificial:
                reasons.append("Contains artificial sweeteners")
            
            # Determine category based on conditions
            if not reasons:
                # All green conditions met
                recommendation_text = "goforit.png"
                recommendation_color = "green"
                text_label = "Go For It!"
                reason = "No added sugar, low total sugar, no artificial sweeteners"
            elif (total_sugar <= 24.0 and added_sugar <= 12.0):
                # Yellow conditions met
                recommendation_text = "oksometimes.png"
                recommendation_color = "yellow"
                text_label = "OK Sometimes"
                # Join all the reasons that prevented it from being green
                reason = ", ".join(reasons)
            else:
                # Red category
                recommendation_text = "maybenot.png"
                recommendation_color = "red"
                text_label = "Maybe Not"
                
                # Add specific red category reasons
                if total_sugar > 24.0:
                    reasons.append("Total sugar exceeds 24g")
                if added_sugar > 12.0:
                    reasons.append("Added sugar exceeds 12g")
                
                # Join all reasons
                reason = ", ".join(reasons)
        
        # Create a new submission record
        new_submission = pd.DataFrame({
            "RowID": [str(uuid.uuid4())],  # Generate a unique ID
            "Timestamp": [date.today().isoformat()],
            "BeverageType": [beverage_type],
            "BeverageName": [input.beverage_name()],
            "Recommendation": [recommendation_color],
            "Reason": [reason if reason else None]
        })
        
        # Update submissions
        current_submissions = submissions.get().copy()
        updated_submissions = pd.concat([current_submissions, new_submission], ignore_index=True)
        submissions.set(updated_submissions)
        
        # Store the result in reactive value
        result = {
            "recommendation": recommendation_text,
            "color": recommendation_color,
            "text_label": text_label
        }
        print(f"Setting recommendation result: {result}")
        recommendation_result.set(result)
    
    # Render recommendation image
    @output
    @render.ui
    def recommendation_image():
        result = recommendation_result.get()
        if result is None:
            return ui.tags.div(
                {"style": "text-align: center;"}, 
                ui.tags.p("Submit the form to see recommendation", 
                          style="text-align: center; color: #666;")
            )
        
        # Map filenames to GitHub URLs
        image_urls = {
            "goforit.png": "https://raw.githubusercontent.com/brendensm/calc-test/main/www/goforit.png",
            "maybenot.png": "https://raw.githubusercontent.com/brendensm/calc-test/main/www/maybenot.png",
            "oksometimes.png": "https://raw.githubusercontent.com/brendensm/calc-test/main/www/oksometimes.png"
        }
        
        # Get the URL for the recommendation - with debug info
        image_url = image_urls.get(result["recommendation"], "")
        print(f"Displaying image: {result['recommendation']} -> {image_url}")
        
        # Return the image UI
        return ui.tags.div(
            {"style": "text-align: center;"},
            ui.tags.img(src=image_url, class_="recommendation")
        )
    
    # Render recommendation text
    @output
    @render.ui
    def recommendation_text():
        result = recommendation_result.get()
        if result is None:
            return ui.tags.div()
        
        # Create a styled text based on the color
        class_name = f"{result['color']}-result"
        return ui.tags.p(result["text_label"], class_=f"recommendation-text {class_name}")

    # Display submissions table
    # @output
    # @render.ui
    # def submissions_table():
    #     df = submissions.get()
    #     
    #     if len(df) == 0:
    #         # Create empty table with headers
    #         columns = ["Date", "Type", "Name", "Result", "Reason"]
    #         return ui.tags.table(
    #             {"class": "table table-striped"},
    #             ui.tags.thead(
    #                 ui.tags.tr([ui.tags.th(col) for col in columns])
    #             ),
    #             ui.tags.tbody(
    #                 ui.tags.tr(ui.tags.td("No data available", colspan=5, style="text-align: center;"))
    #             )
    #         )
    #     else:
    #         # Rename columns for display
    #         display_df = df.copy().rename(columns={
    #             "Timestamp": "Date",
    #             "BeverageType": "Type",
    #             "BeverageName": "Name",
    #             "Recommendation": "Result",
    #             "Reason": "Reason"
    #         })
    #         
    #         # Get columns and data
    #         columns = display_df.columns.tolist()
    #         
    #         # Create table header
    #         thead = ui.tags.thead(
    #             ui.tags.tr([ui.tags.th(col) for col in columns])
    #         )
    #         
    #         # Create table rows
    #         rows = []
    #         for _, row in display_df.iterrows():
    #             cells = []
    #             for col in columns:
    #                 cell_value = row[col] if not pd.isna(row[col]) else ""
    #                 cells.append(ui.tags.td(str(cell_value)))
    #             rows.append(ui.tags.tr(cells))
    #         
    #         # Create table body
    #         tbody = ui.tags.tbody(rows)
    #         
    #         # Return complete table
    #         return ui.tags.table(
    #             {"class": "table table-striped"},
    #             thead,
    #             tbody
    #         )
    
    @output
    @render.ui
    def submissions_table():
        df = submissions.get()
        
        if len(df) == 0:
            # Create empty table with headers
            columns = ["Date", "Type", "Name", "Result", "Reason", "Actions"]
            return ui.tags.table(
                {"class": "table table-striped"},
                ui.tags.thead(
                    ui.tags.tr([ui.tags.th(col) for col in columns])
                ),
                ui.tags.tbody(
                    ui.tags.tr(ui.tags.td("No data available", colspan=6, style="text-align: center;"))
                )
            )
        else:
            # Rename columns for display
            display_df = df.copy().rename(columns={
                "Timestamp": "Date",
                "BeverageType": "Type",
                "BeverageName": "Name",
                "Recommendation": "Result",
                "Reason": "Reason"
            })
            
            # Get columns for display (exclude RowID)
            display_columns = [col for col in display_df.columns if col != "RowID"]
            
            # Create table header (add Actions column)
            all_columns = display_columns + ["Actions"]
            thead = ui.tags.thead(
                ui.tags.tr([ui.tags.th(col) for col in all_columns])
            )
            
            # Create table rows with UUID-based delete buttons
            rows = []
            for idx, row_data in display_df.iterrows():
                row_id = row_data["RowID"]  # Get the unique row ID
                
                cells = []
                for col in display_columns:
                    cell_value = row_data[col] if not pd.isna(row_data[col]) else ""
                    cells.append(ui.tags.td(str(cell_value)))
                
                # Add delete button cell with row UUID
                delete_btn = ui.tags.button(
                    ui.tags.i({"class": "fas fa-trash"}),
                    {"class": "btn btn-sm btn-danger delete-row", 
                     "type": "button",
                     "onclick": f"Shiny.setInputValue('delete_row_id', '{row_id}')"}
                )
                cells.append(ui.tags.td(delete_btn))
                
                rows.append(ui.tags.tr(cells))
            
            # Create table body
            tbody = ui.tags.tbody(rows)
            
            # Return complete table
            return ui.tags.table(
                {"class": "table table-striped"},
                thead,
                tbody
            )


   # Save data to Google Sheet
    @reactive.Effect
    @reactive.event(input.save_data)
    async def save_data():
        # Show saving notification
        ui.notification_show(
            "Saving data to Google Sheet...",
            type="default",
            duration=None,
            id="saving"
        )
        
        current_data = submissions.get()
        
        # Check if there's data to save
        if len(current_data) == 0:
            ui.notification_remove("saving")
            ui.notification_show(
                "No data to save",
                type="warning"
            )
            return
        
        # Convert DataFrame to JSON
        data_json = current_data.to_json(orient="records")
        
        # Google Apps Script URL
        script_url = "https://script.google.com/macros/s/AKfycby6D2dpPUHUrPSzl-mXoVWGuhpYOrORQScpEsWN8zHy_01-0NORjVRgtX0VnvAFkHkHeA/exec"
        
        try:
            # Handle the request based on environment
            if is_pyodide_environment():
                # For Shinylive environment (browser)
                # Use PyJS to make a fetch with no-cors mode
                from js import fetch, Object, JSON
                from pyodide.ffi import to_js
                
                # Convert the data to JavaScript format
                js_data = to_js(json.loads(data_json))
                
                # Create request options
                options = Object.fromEntries(to_js({
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": JSON.stringify(js_data),
                    "mode": "no-cors"  # Add this line to use no-cors mode
                }))
                
                # Use JavaScript's fetch directly
                response = await fetch(script_url, options)
                
                # Since no-cors returns an opaque response, we can't check status
                # Just assume it worked if no exception
                ui.notification_remove("saving")
                ui.notification_show(
                    "Data sent to the server (no confirmation available)",
                    type="success"
                )
            else:
                # For local environment
                response = requests.post(
                    script_url,
                    headers={"Content-Type": "application/json"},
                    data=data_json
                )
                
                # Remove saving notification
                ui.notification_remove("saving")
                
                # Check response status
                if response.status_code == 200:
                    ui.notification_show(
                        "Data saved successfully!",
                        type="success"
                    )
                else:
                    ui.notification_show(
                        f"Error: Server returned status {response.status_code}",
                        type="error"
                    )
                
        except Exception as e:
            # Remove saving notification
            ui.notification_remove("saving")
            
            # Show error notification
            ui.notification_show(
                f"Error: {str(e)}",
                type="error"
            )


            
    @reactive.Effect
    @reactive.event(input.delete_row_id)
    def handle_delete_row():
        # Get the row ID to delete
        row_id = input.delete_row_id()
        
        if row_id:
            # Copy the current dataframe
            current_data = submissions.get().copy()
            
            # Find the row with the matching ID
            matching_rows = current_data["RowID"] == row_id
            
            if matching_rows.any():
                # Drop the row with the matching ID
                updated_data = current_data[~matching_rows].reset_index(drop=True)
                
                # Update the reactive value
                submissions.set(updated_data)
                


# Create app
app = App(app_ui, server)
