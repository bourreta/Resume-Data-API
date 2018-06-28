
import sys
sys.path.insert(0, 'libs')
import rda_keys
from google.appengine.ext import ndb
from google.appengine.api import urlfetch
import urllib
import os
import string
import random
from google.appengine.ext.webapp import template
from google.net.proto.ProtocolBuffer import ProtocolBufferDecodeError
from google.appengine.api.datastore_errors import BadValueError
import webapp2
import types
import json
import datetime

INVALID_TOKEN_ERROR = "Invalid token: acquire new token at "

#Setup authorization variables
client_id = rda_keys.client_id
client_secret = rda_keys.client_secret
redirect_uri = rda_keys.redirect_uri
scope = rda_keys.scope
get_token_url = rda_keys.get_token_url
google_plus_url = rda_keys.google_plus_url
BASE_URL = rda_keys.BASE_URL

#User Model
class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    resume_documents = ndb.StringProperty(repeated=True)
    phone = ndb.StringProperty()
#Resume Model
class Resume(ndb.Model):
    title = ndb.StringProperty(required=True)
    experience = ndb.StringProperty(repeated=True)
    skills = ndb.StringProperty(repeated=True)
    public = ndb.BooleanProperty(required=True)
    date_modified = ndb.DateProperty()
    user_id = ndb.StringProperty()
#Experience Model
class Experience(ndb.Model):
    position_title = ndb.StringProperty(required=True)
    organization = ndb.StringProperty()
    location = ndb.StringProperty()
    type = ndb.StringProperty()
    start_date = ndb.DateProperty()
    end_date = ndb.DateProperty()
    description = ndb.TextProperty()
    user_id = ndb.StringProperty()
# Help functions
def send_error(self, status_code, message):
    self.response.status = status_code
    self.response.write("ERROR: " + message)

def date_to_str(date):
    if date is None:
        return None
    else:
        return date.strftime("%Y-%m-%d")

def str_to_date(datestring):
    return datetime.datetime.strptime(datestring, "%Y-%m-%d")

def check_date(datestring):
    if datestring is not None:
        try:
            datetime.datetime.strptime(datestring, "%Y-%m-%d")
        except ValueError:
            return False
        return True

# Check if token is valid
# Return boolean true/false, dict with user info
def check_token(headers):
    if not headers.has_key('authorization'):
        return False, None
    else:
        token = headers['authorization']

    header = {"authorization": token}
    check_user_result = urlfetch.fetch(
    url=google_plus_url,
    method=urlfetch.GET,
    headers=header
    )

    user_info = json.loads(check_user_result.content)
    
    if not "error" in user_info.keys():
        user = User.query(User.email == user_info["emails"][0]["value"]).fetch()

        if len(user) > 0:
            return True, user[0]
        else:
            new_user = User(name=user_info["name"]["givenName"] + " " + user_info["name"]["familyName"], email=user_info["emails"][0]["value"])
            new_user.put()
            return True, new_user
    else:
        return False, None
# Routes Handlers
# Handle User requests
class UserHandler(webapp2.RequestHandler):
# Get user
    def get(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)

        if token_is_valid:
            if id != None:
                try:
                    user = ndb.Key(urlsafe=id).get()
                    if user.key.urlsafe() != user_data.key.urlsafe():
                        send_error(self, 403, "Forbidden. See " + BASE_URL + " for documentation.")
                        return
                except (ProtocolBufferDecodeError, TypeError):
                    send_error(self, 404, "Not found. Visit " + BASE_URL + "for documentation.")
                    return
            user_dict = user_data.to_dict()
            user_dict['self'] = "/user/" + user_data.key.urlsafe()
            self.response.content_type = "application/json"
            self.response.write(json.dumps(user_dict))
        else:
            send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
            return
# Update user
    def patch(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if token_is_valid:
            try:
                if id:
                    user = ndb.Key(urlsafe=id).get()
                    if user.key.urlsafe() != user_data.key.urlsafe():
                        send_error(self, 403, "Forbidden. See " + BASE_URL + " for documentation.")
                        return
            except (TypeError, AttributeError, ProtocolBufferDecodeError):
                send_error(self, 404, "Not found. Visit " + BASE_URL + "for documentation.")
                return

            try:
                user_patch_data = json.loads(self.request.body)

            except ValueError:
                send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                return

            if not user_patch_data.has_key('phone'):
                send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
  
                return
            else:
                if not isinstance(user_patch_data['phone'], basestring):
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return
                else:
                    user_data.phone = user_patch_data['phone']
                    user_data.put()
                    user_dict = user_data.to_dict()
                    user_dict['self'] = "/user/" + user_data.key.urlsafe()

                    self.response.content_type = "application/json"
                    self.response.write(json.dumps(user_dict))
        else:
            send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
            return
# Handle experience requests
class ExperienceHandler(webapp2.RequestHandler):
    def get(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        
        if token_is_valid:
            if id:
                try:
                    experience = ndb.Key(urlsafe=id).get()
                    
                    if user_data.key.urlsafe() != experience.user_id:
                        send_error(self, 403, "Forbidden. See " + BASE_URL + " for documentation.")
                        return
                except (ProtocolBufferDecodeError, TypeError, AttributeError):
                    send_error(self, 404, "Not found. Visit " + BASE_URL + "for documentation.")
                    return
                    
                experience_dict = experience.to_dict()
                experience_dict['start_date'] = date_to_str(experience_dict['start_date'])
                experience_dict['end_date'] = date_to_str(experience_dict['end_date'])
                experience_dict['self'] = "/experience/" + experience.key.urlsafe()
                experience_dict['user_id'] = "/user/" + experience_dict['user_id']
                self.response.content_type = "application/json"
                self.response.write(json.dumps(experience_dict))
        
            else:
                experiences = Experience.query(Experience.user_id==user_data.key.urlsafe()).fetch()
                experiences_dicts = []
                for i in range(0, len(experiences)):
                    experiences_dicts.append(experiences[i].to_dict())
                    experiences_dicts[i]['start_date'] = date_to_str(experiences[i].start_date)
                    experiences_dicts[i]['end_date'] = date_to_str(experiences[i].end_date)
                    experiences_dicts[i]['self'] = "/experience/" + experiences[i].key.urlsafe()
                    experiences_dicts[i]['user_id'] = "/user/" + experiences_dicts[i]['user_id']
    
                self.response.content_type = "application/json"
                self.response.write(json.dumps(experiences_dicts))
        else:
            send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
            return
# Create new experience
    def post(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if not id:
            if token_is_valid:
                try:
                    experience_data = json.loads(self.request.body)
                except ValueError:
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return
                
                if not (experience_data.has_key('position_title') and experience_data.has_key('organization') and experience_data.has_key('location') and experience_data.has_key('type') and experience_data.has_key('start_date') and experience_data.has_key('end_date') and experience_data.has_key('description')):
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return
                else:
                    if not (isinstance(experience_data['position_title'], basestring) and isinstance(experience_data['organization'], basestring) and isinstance(experience_data['location'], basestring) and isinstance(experience_data['type'], basestring) and check_date(experience_data['start_date']) and (check_date(experience_data['end_date']) or experience_data['end_date'] == None) and isinstance(experience_data['description'], basestring)):
                        send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                        return
                    else:
                        experience_data['start_date'] = str_to_date(experience_data['start_date'])
                        if experience_data['end_date'] is not None:
                            experience_data['end_date'] = str_to_date(experience_data['end_date'])
                    
                        user_id = user_data.key.urlsafe()
                        
                        new_experience = Experience(position_title=experience_data['position_title'], organization=experience_data['organization'], location=experience_data['location'], type=experience_data['type'], start_date=experience_data['start_date'], end_date=experience_data['end_date'], description=experience_data['description'], user_id=user_id)
                        
                        new_experience.put()
                        
                        new_experience_dict = new_experience.to_dict()
                        
                        new_experience_dict['start_date'] = date_to_str(new_experience_dict['start_date'])
                        new_experience_dict['end_date'] = date_to_str(new_experience_dict['end_date'])
                        new_experience_dict['self'] = "/experience/" + new_experience.key.urlsafe()
                        new_experience_dict['user_id'] = "/user/" + user_id
                        self.response.content_type = "application/json"
                        self.response.write(json.dumps(new_experience_dict))
            else:
                send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
                return
        else:
            send_error(self, 404, "Not found. Visit " + BASE_URL + "for documentation.")
            return
# Update an experience
    def patch(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if not token_is_valid:
            send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
            return
        
        if id:
            try:
                experience_patch_data = json.loads(self.request.body)
                experience = ndb.Key(urlsafe=id).get()
                if experience.user_id != user_data.key.urlsafe():
                    send_error(self, 403, "Forbidden. See " + BASE_URL + " for documentation.")
                    return
            except (ValueError, ProtocolBufferDecodeError):
                send_error(self, 404, "Not found. Visit " + BASE_URL + "for documentation.")
                return
            # Validation
            data_is_good = True
            if experience_patch_data.has_key('position_title'):
                if isinstance(experience_patch_data['position_title'], basestring):
                    experience.position_title = experience_patch_data['position_title']
                else:
                    data_is_good = False
            if experience_patch_data.has_key('organization'):
                if isinstance(experience_patch_data['organization'], basestring):
                    experience.organization = experience_patch_data['organization']
                else:
                    data_is_good = False
            if experience_patch_data.has_key('location'):
                if isinstance(experience_patch_data['location'], basestring):
                    experience.location = experience_patch_data['location']
                else:
                    data_is_good = False
            if experience_patch_data.has_key('type'):
                if isinstance(experience_patch_data['type'], basestring):
                    experience.type = experience_patch_data['type']
                else:
                    data_is_good = False
            if experience_patch_data.has_key('description'):
                if isinstance(experience_patch_data['description'], basestring):
                    experience.description = experience_patch_data['description']
                else:
                    data_is_good = False
            if experience_patch_data.has_key('start_date'):
                if isinstance(experience_patch_data['start_date'], basestring):
                    experience.start_date = str_to_date(experience_patch_data['start_date'])
                else:
                    data_is_good = False
            if experience_patch_data.has_key('end_date'):
                if isinstance(experience_patch_data['end_date'], basestring) or experience_patch_data['end_date'] == None:
                    if experience_patch_data['end_date'] != None:
                        experience.end_date = str_to_date(experience_patch_data['end_date'])
                    else:
                        experience.end_date = None

                else:
                    data_is_good = False

            if not data_is_good:
                send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                return
            else:
                experience.put()
                experience_dict = experience.to_dict()
                experience_dict['start_date'] = date_to_str(experience_dict['start_date'])
                experience_dict['end_date'] = date_to_str(experience_dict['end_date'])
                experience_dict['self'] = "/experience/" + experience.key.urlsafe()
                experience_dict['user_id'] = "/user/" + experience_dict['user_id']
                self.response.content_type = "application/json"
                self.response.write(json.dumps(experience_dict))
        else:
            send_error(self, 404, "Not found. Visit " + BASE_URL + "for documentation.")
            return
# Update a single item of an experience
    def put(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if id:
            if not token_is_valid:
                send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
                return

            try:
                experience = ndb.Key(urlsafe=id).get()
                user = ndb.Key(urlsafe=experience.user_id).get()
            except(ProtocolBufferDecodeError, TypeError, AttributeError):
                send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                return

            if user.key.urlsafe() != user_data.key.urlsafe():
                send_error(self, 403, "Forbidden. Visit " + BASE_URL + " for documentation.")
                return

            try:
                experience_data = json.loads(self.request.body)
            except ValueError:
                send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                return

            if not (experience_data.has_key('position_title') and experience_data.has_key('organization') and experience_data.has_key('location') and experience_data.has_key('type') and experience_data.has_key('start_date') and experience_data.has_key('end_date') and experience_data.has_key('description')):
                send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                return
            else:
                if not (isinstance(experience_data['position_title'], basestring) and isinstance(experience_data['organization'], basestring) and isinstance(experience_data['location'], basestring) and isinstance(experience_data['type'], basestring) and check_date(experience_data['start_date']) and (check_date(experience_data['end_date']) or experience_data['end_date'] == None) and isinstance(experience_data['description'], basestring)):
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return
                else:
                    experience.start_date = str_to_date(experience_data['start_date'])
                    if experience_data['end_date'] is not None:
                        experience.end_date = str_to_date(experience_data['end_date'])
                    else:
                        experience.end_date = None
                            
                    experience.position_title = experience_data['position_title']
                    experience.organization = experience_data['organization']
                    experience.location = experience_data['location']
                    experience.description = experience_data['description']
                    experience.type = experience_data['type']
                        
                    experience.put()

                    experience_dict = experience.to_dict()
                    experience_dict['start_date'] = date_to_str(experience.start_date)
                    experience_dict['end_date'] = date_to_str(experience.end_date)
                    experience_dict['self'] = "/experience/" + experience.key.urlsafe()
                    experience_dict['user_id'] = "/user/" + experience.user_id

                    self.response.content_type = "application/json"
                    self.response.write(json.dumps(experience_data))
        else:
            send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
            return
# Delete experience
    def delete(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if not token_is_valid:
            send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
            return
        if id:
            try:
                experience = ndb.Key(urlsafe=id).get()
                user = ndb.Key(urlsafe=experience.user_id).get()
                if user == None:
                    send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                    return
            except (ProtocolBufferDecodeError, TypeError, AttributeError):
                send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                return
            
            if user.key.urlsafe() != user_data.key.urlsafe():
                send_error(self, 403, "Forbidden. Visit " + BASE_URL + " for documentation.")
                return
            # Remove from existing resumes
            resumes = Resume.query(Resume.user_id == user_data.key.urlsafe()).fetch()

            for i in range(0, len(resumes)):
                while id in resumes[i].experience:
                    resumes[i].experience.remove(id)
                resumes[i].put()
                    
            experience.key.delete()
            self.response.status = 204
            self.response.write("Experience deleted.")
        else:
            send_error(self, 404, "Not found. Visit " + BASE_URL + "for documentation.")
            return
# Handle resume requests
class ResumeHandler(webapp2.RequestHandler):
    def get(self, id=None):
        
        token_is_valid, user_data = check_token(self.request.headers)
    
        if id:
            try:
                resume = ndb.Key(urlsafe=id).get()
                user = ndb.Key(urlsafe=resume.user_id).get()
            except:
                send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                return
    
            resume_dict = resume.to_dict()
            if resume_dict['public'] == True:
                contact_info = ndb.Key(urlsafe=resume_dict['user_id']).get()
                contact_info_dict = contact_info.to_dict()
                del resume_dict['user_id']
            elif token_is_valid:
                if user.key.urlsafe() != user_data.key.urlsafe():
                    send_error(self, 403, "Forbidden. Visit " + BASE_URL + " for documentation.")
                    return
                else:
                    contact_info_dict = user_data.to_dict()
            elif not token_is_valid:
                send_error(self, 401, "Unauthorized. Visit " + BASE_URL + " for documentation.")
                return
                
            del contact_info_dict['resume_documents']
            resume_dict['contact_info'] = contact_info_dict
            resume_dict['date_modified'] = date_to_str(resume_dict['date_modified'])
            resume_dict['self'] = "/resume/" + resume.key.urlsafe()
            resume_dict['experience'] = []
            for i in resume.experience:
                exp = ndb.Key(urlsafe=i).get()
                if exp != None:
                    exp = exp.to_dict()
                    exp['start_date'] = date_to_str(exp['start_date'])
                    exp['end_date'] = date_to_str(exp['end_date'])
                    if token_is_valid:
                        exp['experience_url'] = "/experience/" + i
                    del exp['user_id']
                    resume_dict['experience'].append(exp)
            self.response.content_type = "application/json"
            self.response.write(json.dumps(resume_dict))
                
        else:
            if token_is_valid:
                try:
                    resumes = Resume.query(Resume.user_id == user_data.key.urlsafe()).fetch()
                except ProtocolBufferDecodeError:
                    send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                    return
                resumes_dicts = []
                for i in range(0, len(resumes)):
                    resumes_dicts.append(resumes[i].to_dict())
                    resumes_dicts[i]['user'] = "/user/ " + resumes[i].user_id
                    del resumes_dicts[i]['user_id']
                    resumes_dicts[i]['self'] = "/resume/" + resumes[i].key.urlsafe()
                    resumes_dicts[i]['date_modified'] = date_to_str(resumes_dicts[i]['date_modified'])
                    resumes_dicts[i]['experience'] = []
                    for j in range(0, len(resumes[i].experience)):
                        exp = ndb.Key(urlsafe=resumes[i].experience[j]).get()
                        if exp != None:
                            exp = exp.to_dict()
                            exp['start_date'] = date_to_str(exp['start_date'])
                            exp['end_date'] = date_to_str(exp['end_date'])
                            del exp['user_id']
                            resumes_dicts[i]['experience'].append(exp)
                self.response.content_type = "application/json"
                self.response.write(json.dumps(resumes_dicts))
            else:
                send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
                return
# Create a resume
    def post(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if token_is_valid:
            try:
                resume_data = json.loads(self.request.body)
            except ValueError:
                send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                return
    
            if not(resume_data.has_key('title') and resume_data.has_key('public') and resume_data.has_key('experience') and resume_data.has_key('skills')):
                send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                return
            else:
                if not((isinstance(resume_data['experience'], list) and not isinstance(resume_data['experience'], basestring))  and (isinstance(resume_data['skills'], list) and not isinstance(resume_data['skills'], basestring)) and isinstance(resume_data['title'], basestring) and (isinstance(resume_data['public'], bool) and isinstance(resume_data['public'], int))):
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return
                else:
                    try:
                        for i in range(0, len(resume_data['experience'])):
                            experience = ndb.Key(urlsafe=resume_data['experience'][i]).get()
                    except:
                        send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                        return
                    
                    user = ndb.Key(urlsafe=user_data.key.urlsafe()).get()

                    new_resume = Resume(title=resume_data['title'], public=resume_data['public'], experience=resume_data['experience'], skills=resume_data['skills'], user_id=user_data.key.urlsafe(), date_modified=datetime.date.today())
                    new_resume.put()
                    user.resume_documents.append(new_resume.key.urlsafe())
                    user.put()
                    
                    new_resume_dict = new_resume.to_dict()
                    new_resume_dict['self'] = "/resume/" + new_resume.key.urlsafe()
                    new_resume_dict['user_id'] = "/user/" + user.key.urlsafe()
                    new_resume_dict['date_modified'] = date_to_str(new_resume_dict['date_modified'])
                    self.response.content_type = "application/json"
                    self.response.write(json.dumps(new_resume_dict))
    
        else:
            send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
# Update single item on resume
    def put(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if id:
            if token_is_valid:
                try:
                    resume = ndb.Key(urlsafe=id).get()
                    user = ndb.Key(urlsafe=resume.user_id).get()
                except(ProtocolBufferDecodeError, TypeError, AttributeError):
                    send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                    return
                        
                if user_data.key.urlsafe() != user.key.urlsafe():
                    send_error(self, 403, "Forbidden. Visit " + BASE_URL + " for documentation.")
                    return

                try:
                    resume_data = json.loads(self.request.body)
                except ValueError:
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return

                if not(resume_data.has_key('title') and resume_data.has_key('public') and resume_data.has_key('experience') and resume_data.has_key('skills')):
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return
                else:
                    if not((isinstance(resume_data['experience'], list) and not isinstance(resume_data['experience'], basestring))  and (isinstance(resume_data['skills'], list) and not isinstance(resume_data['skills'], basestring)) and isinstance(resume_data['title'], basestring) and type(resume_data['public'] == types.BooleanType)):
                        send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                        return
                    else:
                        
                        try:
                            for i in range(0, len(resume_data['experience'])):
                                experience = ndb.Key(urlsafe=resume_data['experience'][i]).get()
                        except:
                            send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                            return

                        resume.title = resume_data['title']
                        resume.experience = resume_data['experience']
                        resume.skills = resume_data['skills']
                        resume.public = resume_data['public']
                        resume.data_modified = datetime.date.today()
                        resume.put()
                        
                        resume_dict = resume.to_dict()
                        
                        resume_dict['date_modified'] = date_to_str(resume.date_modified)
                        resume_dict['self'] = "/resume/" + resume.key.urlsafe()
                        resume_dict['user_id'] = "/user/" + user.key.urlsafe()
                        
                        self.response.content_type = "application/json"
                        self.response.write(json.dumps(resume_dict))
            
                try:
                    resume_data = json.loads(self.response.body)
                except ValueError:
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return
                    
            else:
                send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
    
        else:
            send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
            return
#Update an entire resume
    def patch(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if token_is_valid:
            if id:
                try:
                    resume = ndb.Key(urlsafe=id).get()
                    user = ndb.Key(urlsafe=resume.user_id).get()
                except (ProtocolBufferDecodeError, TypeError, AttributeError):
                    send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                    return
            
                if user_data.key.urlsafe() != user.key.urlsafe():
                    send_error(self, 403, "Forbidden. Visit " + BASE_URL + " for documentation.")
                    return
                
                try:
                    resume_data = json.loads(self.request.body)
                except ValueError:
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return
                        
                data_is_good = True
                    
                if resume_data.has_key('title'):
                    if(isinstance(resume_data['title'], basestring)):
                        resume.title = resume_data['title']
                    else:
                        data_is_good = False
                if resume_data.has_key('skills'):
                    if(not isinstance(resume_data['skills'], basestring) and isinstance(resume_data['skills'], list)):
                        resume.skills = resume.skills + resume_data['skills']
                    else:
                        data_is_good = False
                if resume_data.has_key('experience'):
                    if(not isinstance(resume_data['experience'], basestring) and isinstance(resume_data['experience'], list)):
                        try:
                            for i in range(0, len(resume_data['experience'])):
                                experience = ndb.Key(urlsafe=resume_data['experience'][i]).get()
                        except:
                            send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                            return
        
                        resume.experience = resume.experience + resume_data['experience']
                    else:
                        data_is_good = False
                if resume_data.has_key('public'):
                    if type(resume_data['public']) == types.BooleanType:
                        resume.public = resume_data['public']
                    else:
                        data_is_good = False
                            
                if data_is_good:
                    resume.date_modified = datetime.date.today()
                    resume.put()
                else:
                    send_error(self, 400, "Invalid request format, visit " + BASE_URL + " for documentation.")
                    return

                resume_dict = resume.to_dict()
                resume_dict['self'] = "/resume/" + resume.key.urlsafe()
                resume_dict['user_id'] = "/user/" + user.key.urlsafe()
                resume_dict['date_modified'] = date_to_str(resume.date_modified)
                self.response.content_type = "application/json"
                self.response.write(json.dumps(resume_dict))
                        
            else:
                send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                return
        else:
            send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
            return
#delete a resume
    def delete(self, id=None):
        token_is_valid, user_data = check_token(self.request.headers)
        if token_is_valid:
            if id:
                try:
                    resume = ndb.Key(urlsafe=id).get()
                    user = ndb.Key(urlsafe=resume.user_id).get()
                    if user.key.urlsafe() != user_data.key.urlsafe():
                        send_error(self, 403, "Forbidden. Visit " + BASE_URL + " for documentation.")
                        return
            
                except (ProtocolBufferDecodeError, TypeError, AttributeError):
                    send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                    return
            
                while id in user.resume_documents:
                    user.resume_documents.remove(id)
            
                user_data.put()
                resume.key.delete()
                self.response.status = 204
                self.response.write("Experience deleted.")
            else:

                send_error(self, 404, "Not found. Visit " + BASE_URL + " for documentation.")
                return
        else:
            send_error(self, 401, INVALID_TOKEN_ERROR + BASE_URL)
            return
# Handle authorization, helping user obtain token
class OauthHandler(webapp2.RequestHandler):
    def get(self):
        
        body = {
            "code": self.request.GET["code"],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        form_data = urllib.urlencode(body)
        headers = {"Content-Type" : "application/x-www-form-urlencoded"}
        post_result = urlfetch.fetch(
            url=get_token_url,
            payload=form_data,
            method=urlfetch.POST,
            headers=headers)
        
        token_data = json.loads(post_result.content)
        header = {"authorization": "Bearer " + token_data["access_token"]}
        get_result = urlfetch.fetch(
            url=google_plus_url,
            method=urlfetch.GET,
            headers=header
        )

        google_plus_info = json.loads(get_result.content)
        template_values = {
            "name": google_plus_info["displayName"],
            "token": token_data["access_token"]
        }
        
        if (google_plus_info.has_key('url')):
            template_values["g_plus_url"] = google_plus_info["url"]

        path = os.path.join(os.path.dirname(__file__), 'result.html')
        self.response.out.write(template.render(path,template_values))

# Main documentation page
class MainPage(webapp2.RequestHandler):
    def get(self):
        state = ""
        
        for i in range(0, 10):
            state +=  random.choice(string.ascii_lowercase + string.digits)
                
        link = "https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=" + client_id + "&redirect_uri=" + redirect_uri + "&scope=" + scope + "&state=" + state
        
        template_values = {"link": link}
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path,template_values))

allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods

# Routes
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/oauth', OauthHandler),
    ('/user', UserHandler),
    ('/user/(.*)', UserHandler),
    ('/experience', ExperienceHandler),
    ('/experience/(.*)', ExperienceHandler),
    ('/resume', ResumeHandler),
    ('/resume/(.*)', ResumeHandler)
], debug=True)

