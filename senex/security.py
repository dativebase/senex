USERS = {'editor':'mookafish',
          'viewer':'mookafish'}
GROUPS = {'editor':['group:editors']}

def groupfinder(userid, request):
    print 'in groupfinder func looking for this id: %s' % userid
    if userid in USERS:
        return GROUPS.get(userid, [])


