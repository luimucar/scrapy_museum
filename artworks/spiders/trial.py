import scrapy



class TrialSpider(scrapy.Spider):
    name = 'trial'
    start_urls = [
        "http://pstrial-a-2018-10-19.toscrape.com/browse/insunsh",
        "http://pstrial-a-2018-10-19.toscrape.com/browse/summertime"
    ]
    site_url = "http://pstrial-a-2018-10-19.toscrape.com"


    def recoverw(self,dictionary,objective, child):
        for k,v in dictionary.items():
            if (objective == k):                
                if child not in v:
                    newchild = {}
                    newchild[child] = []
                    v.append(newchild)
                return
            for item in v:            
                if isinstance(item,dict): self.recoverw(item,objective,child)


    def getPath(self,dictionary,objective):
        for k,v in dictionary.items():
            if (objective == k): 
                nl = []
                nl.append(k)           
                return nl
            else:
                for item in v:            
                    if isinstance(item,dict): 
                        element = self.getPath(item,objective)
                        if element: 
                            nl = []
                            nl.append(k)           
                            return nl + element
        


    def parse(self, response):
        if "type" in response.meta:
            call_type = response.meta["type"]
        else:
            call_type = 'M'


        #Get the category by saving in meta the parent and the tree structure that will be built
        #as the requests get completed 
        current = response.xpath('//div[@id="body"]/h1/text()').get()   
        index = current.find('Browse - ')
        current = current[index+9:]
        structure = ""
        parent = ""
        
        # Only calculate the tree structure for the M type pages.
        if call_type == 'M':        
            if "parent" in response.meta:
                parent = response.meta["parent"]
            else:
                parent = current

            if "structure" in response.meta:
                structure = response.meta["structure"]
                self.recoverw(structure,parent,current)
        
            else:
                structure = {}
                structure[current] = []
            
            #update the parent
            parent = current
            #get the path for this M page
            category = self.getPath(structure,current)
            #yield{
            #    "current": current,
            #    "category": category
            #}

        # Only calculate the tree structure for the M type pages but forward category for P type.
        if call_type=='P': 
            category = response.meta["category"]

        # Get the detail pages (type = D)
        all_a = response.css('a::attr(href)').extract()
        subs = "/item/"
        urls = [i for i in all_a if subs in i]
        for url in urls:   
            url = response.urljoin(url)
            yield scrapy.Request(url = url, callback = self.parse_details, meta = {'category': category,'type':'D'})
        

        # Which next page will be selected?
        nextpage = 1
        next_page_url = response.xpath('//a[re:test(., "^Next")]//@href').extract_first()
        if next_page_url:
            index = next_page_url.find('?page=')
            nextpage = int(next_page_url[index+6:])

        # Get the next pages (type = P)        
        if next_page_url:
            next_page_url = response.urljoin(next_page_url)
            #if nextpage < 2:
            yield scrapy.Request(url = next_page_url, callback = self.parse, meta = {'structure': structure,'parent': parent,'type': 'P','category': category})
        
      
        # Get the browsing structure pages (type = M)       
        if nextpage==1: #only for pages 0-1 have to check the browsing structure
            browse_url = response.xpath("//a/@href[re:test(., 'browse')]").extract()
            
            #Trick to capture only the links of the childs of this section.
            current_url = [i for i in browse_url if '/..' in i]
            
            index = current_url[0].find('/..')
            portion = current_url[0][0:index+1]
            part_url = [w.replace(portion, '') for w in browse_url]
            part_url.remove('..')
            child_url = [i for i in part_url if "/" not in i]
            browse_url = [portion +s for s in child_url]
            
            for url in browse_url:   
                url = response.urljoin(url)
                yield scrapy.Request(url = url, callback = self.parse, meta = {'structure': structure, 'parent': parent,'type': 'M'})
        
        
        
        

    def parse_details(self,response):
        height = ""
        width = ""
        
        category = response.meta["category"]
        dimen = response.css('dl > dd::text').extract()
        if len(dimen) >= 2:
            index_b = dimen[2].find("(")
            index_e = dimen[2].find(")")
            
            if(index_b > 0 and index_e > 0):
                dimcm = dimen[2][index_b+1:index_e]
                index_x = dimcm.find("x")
                index_cm = dimcm.find("cm")
                if(index_x > 0 and index_cm > 0):
                    height = dimcm[0:index_x].strip()
                    width = dimcm[index_x+1:index_cm].strip()
                    index_3rd = width.find('x')
                    if index_3rd > 0:
                        width = width[0:index_3rd].strip()
        image = ""
        img_ = response.css('img::attr(src)').extract_first()
        if img_:
            image = self.site_url+img_
            
        artist =  response.xpath('//h2[@itemprop="artist"]/text()').get()
        if artist:
            index = artist.find('Artist:')
            if index >= 0:
                artist = artist[0:index]

        yield{
            'url':response.url,
            'artist':artist,
            'title': response.css('h1::text').extract_first(),
            'image': image,
            'height': height,  
            'width': width, 
            'description': response.xpath('//div[@itemprop="description"]/p/text()').get(),
            'categories': category
            
        }

    