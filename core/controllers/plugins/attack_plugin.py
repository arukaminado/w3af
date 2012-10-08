'''
AttackPlugin.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import copy

import core.controllers.outputManager as om
import core.data.request.HTTPPostDataRequest as HTTPPostDataRequest
import core.data.kb.knowledgeBase as kb

from core.controllers.w3afException import w3afException
from core.controllers.plugins.plugin import Plugin
from core.controllers.misc.common_attack_methods import CommonAttackMethods
from core.data.parsers.urlParser import url_object


class AttackPlugin(Plugin, CommonAttackMethods):
    '''
    This is the base class for attack plugins, all attack plugins should inherit from it 
    and implement the following methods :
        1. fastExploit(...)
        2. _generate_shell(...)
        
    @author: Andres Riancho ((andres.riancho@gmail.com))
    '''

    def __init__(self):
        Plugin.__init__( self )
        CommonAttackMethods.__init__( self )
        
        self._uri_opener = None
        self._footer = None
        self._header = None
        
        # User configured parameter
        self._generate_only_one = False

    def fastExploit(self, url ):
        '''
        '''
        raise NotImplementedError('Plugin is not implementing required method fastExploit' )
        
    def _generate_shell( self, vuln ):
        '''
        @parameter vuln: The vulnerability object to exploit.
        '''
        raise NotImplementedError('Plugin is not implementing required method _generate_shell' )
        
    def getExploitableVulns(self):
        return kb.kb.get( self.getVulnName2Exploit() , self.getVulnName2Exploit() )
        
    def canExploit(self, vulnToExploit=None):
        '''
        Determines if audit plugins found exploitable vulns.
        
        @parameter vulnToExploit: The vulnerability id to exploit
        @return: True if we can exploit a vuln stored in the kb.
        '''
        vulns = self.getExploitableVulns()
        if vulnToExploit is not None:
            vulns = [ v for v in vulns if v.getId() == vulnToExploit ]
            if vulns:
                return True
            else:
                return False
        else:
            # The user didn't specified what vuln to exploit... so...
            if vulns:
                return True
            else:
                return False

    def getAttackType(self):
        '''
        @return: The type of exploit, SHELL, PROXY, etc.
        '''
        raise NotImplementedError('Plugin is not implementing required method getAttackType' )

    def GET2POST( self, vuln ):
        '''
        This method changes a vulnerability mutant, so all the data that was sent in the query string,
        is now sent in the postData; of course, the HTTP method is also changed from GET to POST.
        '''
        vulnCopy = copy.deepcopy( vuln )
        mutant = vulnCopy.getMutant()
        
        #    Sometimes there is no mutant (php_sca).
        if mutant is None:
            return vulnCopy
        
        if mutant.get_method() == 'POST':
            # No need to work !
            return vulnCopy
            
        else:
            pdr = HTTPPostDataRequest.HTTPPostDataRequest(
                                              mutant.getURL(),
                                              headers=mutant.getHeaders(),
                                              cookie=mutant.getCookie(),
                                              dc=mutant.getDc()
                                              )
            mutant.setFuzzableReq(pdr)
            return vulnCopy
            
    def getRootProbability( self ):
        '''
        @return: This method returns the probability of getting a root shell using this attack plugin.
        This is used by the "exploit *" function to order the plugins and first try to exploit the more critical ones.
        This method should return 0 for an exploit that will never return a root shell, and 1 for an exploit that WILL ALWAYS
        return a root shell.
        '''
        raise NotImplementedError( 'Plugin is not implementing required method getRootProbability' )
        
    def getType( self ):
        return 'attack'
        
    def getVulnName2Exploit( self ):
        '''
        This method should return the vulnerability name (as saved in the kb) to exploit.
        For example, if the audit.os_commanding plugin finds an vuln, and saves it as:
        
        kb.kb.append( 'os_commanding' , 'os_commanding', vuln )
        
        Then the exploit plugin that exploits os_commanding ( attack.os_commanding ) should
        return 'os_commanding' in this method.
        '''
        raise NotImplementedError( 'Plugin is not implementing required method getVulnName2Exploit' )
    
    def exploit( self, vulnToExploit=None):
        '''
        Exploits a vuln that was found and stored in the kb.
        
        @parameter vulnToExploit: The vulnerability id to exploit
        @return: A list of shells of proxies generated by the exploitation phase
        '''
        om.out.information( self.getName() + ' exploit plugin is starting.' )
        if not self.canExploit():
            raise w3afException('No '+ self.getVulnName2Exploit() + ' vulnerabilities have been found.')

        for vuln in self.getExploitableVulns():
            
            if vulnToExploit is not None:
                if vulnToExploit != vuln.getId():
                    continue
                
            #
            #   A couple of minor verifications before continuing to exploit a vulnerability
            #                
            if not isinstance( vuln.getURL(), url_object):
                msg = '%s plugin can NOT exploit vulnerability with id "%s" as it doesn\'t have an URL.'
                om.out.debug( msg % (self.getName(), vuln.getId()) )
                continue

            if not isinstance( vuln.get_method(), basestring):
                msg = '%s plugin can NOT exploit vulnerability with id "%s" as it doesn\'t have an HTTP method.'
                om.out.debug( msg % (self.getName(), vuln.getId()) )
                continue
                    
            # Try to get a shell using a vuln
            s = self._generate_shell(vuln)
            if s is not None:
                kb.kb.append( self, 'shell', s )
                om.out.console('Vulnerability successfully exploited. Generated shell object %s' % s)
                if self._generate_only_one:
                    # A shell was generated, I only need one point of exec.
                    return [s,]
                else:
                    # Keep adding all shells to the kb
                    # this is done 5 lines before this comment
                    pass
        
        return kb.kb.get( self.getName(), 'shell' )

    def get_plugin_deps( self ):
        '''
        @return: A list with the names of the plugins that should be run before the
        current one. For attack plugins this doesn't make much sense since we're not
        doing anything with the output from this method.
        '''
        return []
