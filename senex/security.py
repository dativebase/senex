USERS = {'editor':'mookafish',
          'viewer':'mookafish'}
GROUPS = {'editor':['group:editors']}

def groupfinder(userid, request):
    if userid in USERS:
        return GROUPS.get(userid, [])


